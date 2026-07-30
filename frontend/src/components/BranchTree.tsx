"use client";

import {
  Trash2,
} from "lucide-react";
import {
  type PointerEvent as ReactPointerEvent,
  useEffect,
  useMemo,
  useRef,
  useState,
} from "react";

import {
  type BranchNode,
  type BranchNodeComment,
  createBranchNodeComment,
  deleteBranchNodeComment,
  listBranchNodeComments,
  listBranchNodePositions,
  resetBranchNodePositions,
  updateBranchNodeComment,
  updateBranchNodePosition,
} from "@/lib/threadApi";
import { DeleteConfirmModal } from "./DeleteConfirmModal";

const NODE_WIDTH = 154;
const NODE_HEIGHT = 48;
const COLUMN_GAP = 92;
const ROW_GAP = 26;
const CANVAS_PADDING = 36;
const COMMENT_RADIUS = 9;
const COMMENT_EDGE_GAP = 24;
const COMMENT_CROSS_OFFSET = 18;
const NODE_TITLE_MAX_CHARS = 14;

type GraphNode = {
  node: BranchNode;
  depth: number;
};

type GraphEdge = {
  fromId: string;
  toId: string;
};

type Position = {
  x: number;
  y: number;
};

type GraphLayout = {
  nodes: GraphNode[];
  edges: GraphEdge[];
  initialPositions: Record<string, Position>;
  width: number;
  height: number;
};

function makeLayout(root: BranchNode): GraphLayout {
  const nodes: GraphNode[] = [];
  const edges: GraphEdge[] = [];
  const levels = new Map<number, GraphNode[]>();
  let maxDepth = 0;

  const visit = (node: BranchNode, depth: number) => {
    const graphNode = { node, depth };
    nodes.push(graphNode);
    levels.set(depth, [...(levels.get(depth) || []), graphNode]);
    maxDepth = Math.max(maxDepth, depth);

    for (const child of node.children || []) {
      edges.push({ fromId: node.id, toId: child.id });
      visit(child, depth + 1);
    }
  };

  visit(root, 0);

  const widestLevel = Math.max(
    1,
    ...Array.from(levels.values(), (level) => level.length),
  );
  const width =
    CANVAS_PADDING * 2 +
    NODE_WIDTH +
    maxDepth * (NODE_WIDTH + COLUMN_GAP);
  const height = Math.max(
    560,
    CANVAS_PADDING * 2 +
      widestLevel * NODE_HEIGHT +
      Math.max(0, widestLevel - 1) * ROW_GAP,
  );
  const initialPositions: Record<string, Position> = {};

  for (const [depth, levelNodes] of levels) {
    const x = CANVAS_PADDING + depth * (NODE_WIDTH + COLUMN_GAP);
    const availableHeight = height - CANVAS_PADDING * 2 - NODE_HEIGHT;
    const step =
      levelNodes.length === 1 ? 0 : availableHeight / (levelNodes.length - 1);

    levelNodes.forEach(({ node }, index) => {
      initialPositions[node.id] = {
        x,
        y:
          levelNodes.length === 1
            ? (height - NODE_HEIGHT) / 2
            : CANVAS_PADDING + index * step,
      };
    });
  }

  return { nodes, edges, initialPositions, width, height };
}

function rectangleConnectionGeometry(
  from: Position,
  to: Position,
  fromWidth: number,
  fromHeight: number,
  toWidth: number,
  toHeight: number,
  minimumCurve = 72,
  horizontalCurveRatio = 0.45,
  verticalCurveRatio = 0,
  verticalBendRatio = 0,
) {
  const fromCenterX = from.x + fromWidth / 2;
  const toCenterX = to.x + toWidth / 2;
  const travelsRight = toCenterX >= fromCenterX;
  const startX = travelsRight ? from.x + fromWidth : from.x;
  const endX = travelsRight ? to.x : to.x + toWidth;
  const startY = from.y + fromHeight / 2;
  const endY = to.y + toHeight / 2;
  const direction = travelsRight ? 1 : -1;
  const verticalDelta = endY - startY;
  const curve = Math.max(
    minimumCurve,
    Math.abs(endX - startX) * horizontalCurveRatio +
      Math.abs(verticalDelta) * verticalCurveRatio,
  );
  const verticalBend = Math.max(
    -110,
    Math.min(110, verticalDelta * verticalBendRatio),
  );

  return {
    path: `M ${startX} ${startY} C ${startX + direction * curve} ${startY + verticalBend}, ${endX - direction * curve} ${endY - verticalBend}, ${endX} ${endY}`,
    startX,
    startY,
    endX,
    endY,
  };
}

function connectionGeometry(from: Position, to: Position) {
  return rectangleConnectionGeometry(
    from,
    to,
    NODE_WIDTH,
    NODE_HEIGHT,
    NODE_WIDTH,
    NODE_HEIGHT,
  );
}

function commentConnectionGeometry(from: Position, to: Position) {
  return rectangleConnectionGeometry(
    from,
    {
      x: to.x - COMMENT_RADIUS,
      y: to.y - COMMENT_RADIUS,
    },
    NODE_WIDTH,
    NODE_HEIGHT,
    COMMENT_RADIUS * 2,
    COMMENT_RADIUS * 2,
    14,
    0.72,
    0.34,
    0.42,
  );
}

function clamp(value: number, min: number, max: number) {
  return Math.min(max, Math.max(min, value));
}

function errorMessage(error: unknown, fallback: string) {
  return error instanceof Error && error.message ? error.message : fallback;
}

function nodeTitle(title?: string | null) {
  const normalized = title || "제목 없는 스레드";
  const characters = Array.from(normalized);
  return characters.length > NODE_TITLE_MAX_CHARS
    ? `${characters.slice(0, NODE_TITLE_MAX_CHARS).join("")}…`
    : normalized;
}

type Props = {
  root: BranchNode;
  token: string;
  onSelect: (threadId: string) => void;
  onDelete?: (node: BranchNode) => void | Promise<void>;
};

export function BranchTree({ root, token, onSelect, onDelete }: Props) {
  const layout = useMemo(() => makeLayout(root), [root]);
  const threadIds = useMemo(
    () => layout.nodes.map(({ node }) => node.id),
    [layout.nodes],
  );
  const [positions, setPositions] = useState(layout.initialPositions);
  const [positionsLoading, setPositionsLoading] = useState(true);
  const [comments, setComments] = useState<BranchNodeComment[]>([]);
  const [commentsLoading, setCommentsLoading] = useState(true);
  const [commentError, setCommentError] = useState<string | null>(null);
  const [zoom, setZoom] = useState(1);
  const [viewportSize, setViewportSize] = useState({ width: 0, height: 0 });
  const [createTargetId, setCreateTargetId] = useState<string | null>(null);
  const [createText, setCreateText] = useState("");
  const [selectedCommentId, setSelectedCommentId] = useState<string | null>(
    null,
  );
  const [editingCommentId, setEditingCommentId] = useState<string | null>(null);
  const [editingText, setEditingText] = useState("");
  const [busyAction, setBusyAction] = useState<string | null>(null);
  const [deleteTarget, setDeleteTarget] = useState<BranchNode | null>(null);
  const viewportRef = useRef<HTMLDivElement | null>(null);
  const nodeDragRef = useRef<{
    id: string;
    pointerId: number;
    originX: number;
    originY: number;
    currentX: number;
    currentY: number;
    startX: number;
    startY: number;
    moved: boolean;
  } | null>(null);
  const commentDragRef = useRef<{
    id: string;
    pointerId: number;
    originX: number;
    originY: number;
    currentX: number;
    currentY: number;
    startX: number;
    startY: number;
    moved: boolean;
  } | null>(null);
  const ignoreNodeClickRef = useRef<string | null>(null);
  const ignoreCommentClickRef = useRef<string | null>(null);
  const touchPointsRef = useRef<Map<number, Position>>(new Map());
  const pinchRef = useRef<{
    initialDistance: number;
    initialZoom: number;
  } | null>(null);
  const suppressCanvasClickRef = useRef(false);

  useEffect(() => {
    setPositions(layout.initialPositions);
    setZoom(1);
    setSelectedCommentId(null);
    setEditingCommentId(null);
  }, [layout]);

  useEffect(() => {
    let active = true;
    setPositionsLoading(true);

    listBranchNodePositions(threadIds, token)
      .then((savedPositions) => {
        if (!active) return;
        setPositions({
          ...layout.initialPositions,
          ...Object.fromEntries(
            savedPositions
              .filter((position) => threadIds.includes(position.thread_id))
              .map((position) => [
                position.thread_id,
                {
                  x: clamp(
                    position.position_x,
                    10,
                    layout.width - NODE_WIDTH - 10,
                  ),
                  y: clamp(
                    position.position_y,
                    10,
                    layout.height - NODE_HEIGHT - 10,
                  ),
                },
              ]),
          ),
        });
      })
      .catch((error) => {
        if (active) {
          setCommentError(
            errorMessage(error, "저장된 브랜치 위치를 불러오지 못했습니다."),
          );
        }
      })
      .finally(() => {
        if (active) setPositionsLoading(false);
      });

    return () => {
      active = false;
    };
  }, [
    layout.height,
    layout.initialPositions,
    layout.width,
    threadIds,
    token,
  ]);

  useEffect(() => {
    let active = true;
    setCommentsLoading(true);
    setCommentError(null);

    listBranchNodeComments(threadIds, token)
      .then((nextComments) => {
        if (!active) return;
        setComments(
          nextComments.map((comment) => ({
            ...comment,
            position_x: clamp(
              comment.position_x,
              COMMENT_RADIUS + 4,
              layout.width - COMMENT_RADIUS - 4,
            ),
            position_y: clamp(
              comment.position_y,
              COMMENT_RADIUS + 4,
              layout.height - COMMENT_RADIUS - 4,
            ),
          })),
        );
      })
      .catch((error) => {
        if (active) {
          setCommentError(
            errorMessage(error, "코멘트를 불러오지 못했습니다."),
          );
        }
      })
      .finally(() => {
        if (active) setCommentsLoading(false);
      });

    return () => {
      active = false;
    };
  }, [layout.height, layout.width, threadIds, token]);

  useEffect(() => {
    const viewport = viewportRef.current;
    if (!viewport) return;

    const updateSize = () => {
      const rect = viewport.getBoundingClientRect();
      setViewportSize({ width: rect.width, height: rect.height });
    };
    updateSize();

    const observer = new ResizeObserver(updateSize);
    observer.observe(viewport);
    return () => observer.disconnect();
  }, []);

  const fitScale =
    viewportSize.width > 0 && viewportSize.height > 0
      ? Math.min(
          (viewportSize.width - 28) / layout.width,
          (viewportSize.height - 28) / layout.height,
          1,
        )
      : 1;
  const renderScale = Math.max(0.25, Math.min(1.6, fitScale * zoom));

  const defaultCommentPosition = (threadId: string) => {
    const nodePosition = positions[threadId] || layout.initialPositions[threadId];
    const parentCenter = {
      x: nodePosition.x + NODE_WIDTH / 2,
      y: nodePosition.y + NODE_HEIGHT / 2,
    };
    const obstacles = [
      ...Object.entries(positions)
        .filter(([nodeId]) => nodeId !== threadId)
        .map(([, position]) => ({
          x: position.x + NODE_WIDTH / 2,
          y: position.y + NODE_HEIGHT / 2,
        })),
      ...comments.map((comment) => ({
        x: comment.position_x,
        y: comment.position_y,
      })),
    ];
    const rightX =
      nodePosition.x + NODE_WIDTH + COMMENT_RADIUS + COMMENT_EDGE_GAP;
    const leftX =
      nodePosition.x - COMMENT_RADIUS - COMMENT_EDGE_GAP;
    const topY =
      nodePosition.y - COMMENT_RADIUS - COMMENT_EDGE_GAP;
    const bottomY =
      nodePosition.y + NODE_HEIGHT + COMMENT_RADIUS + COMMENT_EDGE_GAP;
    const candidates: Position[] = [
      { x: rightX, y: parentCenter.y + COMMENT_CROSS_OFFSET },
      { x: rightX, y: parentCenter.y - COMMENT_CROSS_OFFSET },
      { x: parentCenter.x + COMMENT_CROSS_OFFSET, y: bottomY },
      { x: parentCenter.x + COMMENT_CROSS_OFFSET, y: topY },
      { x: leftX, y: parentCenter.y + COMMENT_CROSS_OFFSET },
      { x: leftX, y: parentCenter.y - COMMENT_CROSS_OFFSET },
      { x: parentCenter.x - COMMENT_CROSS_OFFSET, y: bottomY },
      { x: parentCenter.x - COMMENT_CROSS_OFFSET, y: topY },
    ].map((candidate) => ({
      x: clamp(
        candidate.x,
        COMMENT_RADIUS + 8,
        layout.width - COMMENT_RADIUS - 8,
      ),
      y: clamp(
        candidate.y,
        COMMENT_RADIUS + 8,
        layout.height - COMMENT_RADIUS - 8,
      ),
    }));

    return candidates.reduce<Position & { score: number }>(
      (best, candidate) => {
        const score =
          obstacles.length === 0
            ? 0
            : Math.min(
                ...obstacles.map((obstacle) =>
                  Math.hypot(
                    candidate.x - obstacle.x,
                    candidate.y - obstacle.y,
                  ),
                ),
              );
        return score > best.score ? { ...candidate, score } : best;
      },
      {
        ...candidates[0],
        score: Number.NEGATIVE_INFINITY,
      },
    );
  };

  const submitNewComment = async () => {
    const content = createText.trim();
    if (!createTargetId || !content || busyAction) return;
    const position = defaultCommentPosition(createTargetId);
    setBusyAction("create");
    setCommentError(null);
    try {
      const created = await createBranchNodeComment(
        {
          thread_id: createTargetId,
          content,
          position_x: position.x,
          position_y: position.y,
        },
        token,
      );
      setComments((current) => [...current, created]);
      setCreateTargetId(null);
      setCreateText("");
      setSelectedCommentId(null);
    } catch (error) {
      setCommentError(errorMessage(error, "코멘트를 저장하지 못했습니다."));
    } finally {
      setBusyAction(null);
    }
  };

  const submitEditedComment = async (commentId: string) => {
    const content = editingText.trim();
    if (!content || busyAction) return;
    setBusyAction(`edit:${commentId}`);
    setCommentError(null);
    try {
      const updated = await updateBranchNodeComment(
        commentId,
        { content },
        token,
      );
      setComments((current) =>
        current.map((comment) =>
          comment.id === commentId ? updated : comment,
        ),
      );
      setEditingCommentId(null);
      setEditingText("");
    } catch (error) {
      setCommentError(errorMessage(error, "코멘트를 수정하지 못했습니다."));
    } finally {
      setBusyAction(null);
    }
  };

  const removeComment = async (commentId: string) => {
    if (busyAction) return;
    setBusyAction(`delete:${commentId}`);
    setCommentError(null);
    try {
      await deleteBranchNodeComment(commentId, token);
      setComments((current) =>
        current.filter((comment) => comment.id !== commentId),
      );
      setSelectedCommentId(null);
      setEditingCommentId(null);
    } catch (error) {
      setCommentError(errorMessage(error, "코멘트를 삭제하지 못했습니다."));
    } finally {
      setBusyAction(null);
    }
  };

  const startNodeDrag = (
    event: ReactPointerEvent<HTMLButtonElement>,
    nodeId: string,
  ) => {
    const position = positions[nodeId];
    if (!position || busyAction || positionsLoading) return;

    event.currentTarget.setPointerCapture(event.pointerId);
    nodeDragRef.current = {
      id: nodeId,
      pointerId: event.pointerId,
      originX: position.x,
      originY: position.y,
      currentX: position.x,
      currentY: position.y,
      startX: event.clientX,
      startY: event.clientY,
      moved: false,
    };
  };

  const moveNodeDrag = (event: ReactPointerEvent<HTMLButtonElement>) => {
    const drag = nodeDragRef.current;
    if (!drag || drag.pointerId !== event.pointerId) return;

    const deltaX = (event.clientX - drag.startX) / renderScale;
    const deltaY = (event.clientY - drag.startY) / renderScale;
    if (Math.abs(deltaX) + Math.abs(deltaY) > 4) drag.moved = true;
    drag.currentX = clamp(
      drag.originX + deltaX,
      10,
      layout.width - NODE_WIDTH - 10,
    );
    drag.currentY = clamp(
      drag.originY + deltaY,
      10,
      layout.height - NODE_HEIGHT - 10,
    );

    setPositions((current) => ({
      ...current,
      [drag.id]: {
        x: drag.currentX,
        y: drag.currentY,
      },
    }));
  };

  const finishNodeDrag = async (
    event: ReactPointerEvent<HTMLButtonElement>,
  ) => {
    const drag = nodeDragRef.current;
    if (!drag || drag.pointerId !== event.pointerId) return;

    if (event.currentTarget.hasPointerCapture(event.pointerId)) {
      event.currentTarget.releasePointerCapture(event.pointerId);
    }
    if (drag.moved) {
      ignoreNodeClickRef.current = drag.id;
      window.setTimeout(() => {
        if (ignoreNodeClickRef.current === drag.id) {
          ignoreNodeClickRef.current = null;
        }
      }, 0);
    }
    nodeDragRef.current = null;
    if (!drag.moved) return;

    setBusyAction(`move-node:${drag.id}`);
    setCommentError(null);
    try {
      const saved = await updateBranchNodePosition(
        drag.id,
        {
          position_x: drag.currentX,
          position_y: drag.currentY,
        },
        token,
      );
      setPositions((current) => ({
        ...current,
        [drag.id]: {
          x: saved.position_x,
          y: saved.position_y,
        },
      }));
    } catch (error) {
      setPositions((current) => ({
        ...current,
        [drag.id]: {
          x: drag.originX,
          y: drag.originY,
        },
      }));
      setCommentError(
        errorMessage(error, "브랜치 위치를 저장하지 못했습니다."),
      );
    } finally {
      setBusyAction(null);
    }
  };

  const resetNodePositions = async () => {
    if (busyAction || positionsLoading) return;
    setBusyAction("reset-nodes");
    setCommentError(null);
    try {
      await resetBranchNodePositions(threadIds, token);
      setPositions(layout.initialPositions);
    } catch (error) {
      setCommentError(
        errorMessage(error, "브랜치 위치를 원래대로 돌리지 못했습니다."),
      );
    } finally {
      setBusyAction(null);
    }
  };

  const startCommentDrag = (
    event: ReactPointerEvent<HTMLButtonElement>,
    comment: BranchNodeComment,
  ) => {
    event.stopPropagation();
    if (!comment.can_edit) return;
    event.currentTarget.setPointerCapture(event.pointerId);
    commentDragRef.current = {
      id: comment.id,
      pointerId: event.pointerId,
      originX: comment.position_x,
      originY: comment.position_y,
      currentX: comment.position_x,
      currentY: comment.position_y,
      startX: event.clientX,
      startY: event.clientY,
      moved: false,
    };
  };

  const moveCommentDrag = (event: ReactPointerEvent<HTMLButtonElement>) => {
    const drag = commentDragRef.current;
    if (!drag || drag.pointerId !== event.pointerId) return;
    const deltaX = (event.clientX - drag.startX) / renderScale;
    const deltaY = (event.clientY - drag.startY) / renderScale;
    if (Math.abs(deltaX) + Math.abs(deltaY) > 4) drag.moved = true;
    drag.currentX = clamp(
      drag.originX + deltaX,
      COMMENT_RADIUS + 4,
      layout.width - COMMENT_RADIUS - 4,
    );
    drag.currentY = clamp(
      drag.originY + deltaY,
      COMMENT_RADIUS + 4,
      layout.height - COMMENT_RADIUS - 4,
    );
    setComments((current) =>
      current.map((comment) =>
        comment.id === drag.id
          ? {
              ...comment,
              position_x: drag.currentX,
              position_y: drag.currentY,
            }
          : comment,
      ),
    );
  };

  const finishCommentDrag = async (
    event: ReactPointerEvent<HTMLButtonElement>,
  ) => {
    const drag = commentDragRef.current;
    if (!drag || drag.pointerId !== event.pointerId) return;
    if (event.currentTarget.hasPointerCapture(event.pointerId)) {
      event.currentTarget.releasePointerCapture(event.pointerId);
    }
    commentDragRef.current = null;

    if (!drag.moved) return;
    ignoreCommentClickRef.current = drag.id;
    window.setTimeout(() => {
      if (ignoreCommentClickRef.current === drag.id) {
        ignoreCommentClickRef.current = null;
      }
    }, 0);

    setBusyAction(`move:${drag.id}`);
    setCommentError(null);
    try {
      const updated = await updateBranchNodeComment(
        drag.id,
        { position_x: drag.currentX, position_y: drag.currentY },
        token,
      );
      setComments((current) =>
        current.map((comment) =>
          comment.id === drag.id ? updated : comment,
        ),
      );
    } catch (error) {
      setComments((current) =>
        current.map((comment) =>
          comment.id === drag.id
            ? {
                ...comment,
                position_x: drag.originX,
                position_y: drag.originY,
              }
            : comment,
        ),
      );
      setCommentError(
        errorMessage(error, "코멘트 위치를 저장하지 못했습니다."),
      );
    } finally {
      setBusyAction(null);
    }
  };

  const startCanvasPointer = (event: ReactPointerEvent<HTMLDivElement>) => {
    if (event.pointerType !== "touch") return;
    touchPointsRef.current.set(event.pointerId, {
      x: event.clientX,
      y: event.clientY,
    });
    if (touchPointsRef.current.size !== 2) return;

    const [first, second] = Array.from(touchPointsRef.current.values());
    pinchRef.current = {
      initialDistance: Math.max(
        1,
        Math.hypot(second.x - first.x, second.y - first.y),
      ),
      initialZoom: zoom,
    };
    nodeDragRef.current = null;
    commentDragRef.current = null;
    suppressCanvasClickRef.current = true;
  };

  const moveCanvasPointer = (event: ReactPointerEvent<HTMLDivElement>) => {
    if (
      event.pointerType !== "touch" ||
      !touchPointsRef.current.has(event.pointerId)
    ) {
      return;
    }
    touchPointsRef.current.set(event.pointerId, {
      x: event.clientX,
      y: event.clientY,
    });
    if (!pinchRef.current || touchPointsRef.current.size < 2) return;

    event.preventDefault();
    const [first, second] = Array.from(touchPointsRef.current.values());
    const distance = Math.max(
      1,
      Math.hypot(second.x - first.x, second.y - first.y),
    );
    setZoom(
      clamp(
        pinchRef.current.initialZoom *
          (distance / pinchRef.current.initialDistance),
        0.6,
        2,
      ),
    );
  };

  const finishCanvasPointer = (event: ReactPointerEvent<HTMLDivElement>) => {
    if (event.pointerType !== "touch") return;
    touchPointsRef.current.delete(event.pointerId);
    if (touchPointsRef.current.size < 2) {
      pinchRef.current = null;
    }
    if (touchPointsRef.current.size === 0) {
      window.setTimeout(() => {
        suppressCanvasClickRef.current = false;
      }, 250);
    }
  };

  const selectedComment =
    comments.find((comment) => comment.id === selectedCommentId) || null;
  const selectedCommentPanelPosition = selectedComment
    ? (() => {
        const panelWidth = 230;
        const panelEstimatedHeight = 250;
        const margin = 8;
        const canvasLeft =
          (viewportSize.width - layout.width * renderScale) / 2;
        const canvasTop =
          (viewportSize.height - layout.height * renderScale) / 2;
        const anchorX =
          canvasLeft + selectedComment.position_x * renderScale;
        const anchorY =
          canvasTop + selectedComment.position_y * renderScale;
        const rightCandidate = anchorX + 16 * renderScale;
        const desiredLeft =
          rightCandidate + panelWidth <= viewportSize.width - margin
            ? rightCandidate
            : anchorX - 16 * renderScale - panelWidth;
        const screenLeft = clamp(
          desiredLeft,
          margin,
          Math.max(margin, viewportSize.width - panelWidth - margin),
        );
        const screenTop = clamp(
          anchorY - 16 * renderScale,
          margin,
          Math.max(
            margin,
            viewportSize.height - panelEstimatedHeight - margin,
          ),
        );
        return {
          left: (screenLeft - canvasLeft) / renderScale,
          top: (screenTop - canvasTop) / renderScale,
        };
      })()
    : null;

  return (
    <div
      ref={viewportRef}
      className="relative h-[min(65dvh,36rem)] min-h-[420px] w-full touch-none select-none overflow-hidden rounded-xl border border-cyan-300/15 bg-slate-950/45 shadow-inner shadow-cyan-950/30 sm:h-[calc(100dvh-15rem)] sm:min-h-[520px] sm:rounded-2xl"
      role="tree"
      aria-busy={commentsLoading || positionsLoading}
      aria-label={`${root.title || "제목 없는 스레드"} 브랜치 트리`}
      onPointerDown={startCanvasPointer}
      onPointerMove={moveCanvasPointer}
      onPointerUp={finishCanvasPointer}
      onPointerCancel={finishCanvasPointer}
    >
      {(commentsLoading || positionsLoading) && (
        <div className="absolute inset-0 z-[60] flex items-center justify-center bg-slate-950/45 px-4 backdrop-blur-[2px]">
          <div
            role="status"
            aria-live="polite"
            className="rounded-2xl border border-cyan-200/20 bg-slate-950/90 px-6 py-5 text-center text-white shadow-2xl shadow-cyan-950/40"
          >
            <span
              aria-hidden="true"
              className="mx-auto block h-9 w-9 animate-spin rounded-full border-[3px] border-cyan-100/20 border-t-cyan-300 shadow-[0_0_18px_rgba(103,232,249,0.28)]"
            />
            <p className="mt-3 text-sm font-semibold text-white">
              브랜치와 코멘트를 불러오는 중...
            </p>
          </div>
        </div>
      )}

      <button
        type="button"
        onClick={() => void resetNodePositions()}
        disabled={Boolean(busyAction) || positionsLoading}
        className="absolute left-2 top-2 z-30 inline-flex min-h-10 items-center justify-center gap-1.5 rounded-xl border border-cyan-200/20 bg-slate-950/85 px-3 py-2 text-[11px] font-semibold text-cyan-50 shadow-lg backdrop-blur transition hover:border-cyan-200/35 hover:bg-cyan-300/10 disabled:cursor-wait disabled:opacity-50 sm:left-3 sm:top-3"
      >
        {busyAction === "reset-nodes" && (
          <span className="h-3.5 w-3.5 animate-spin rounded-full border-2 border-cyan-100 border-t-transparent" />
        )}
        원래대로
      </button>

      <div
        aria-label="화면 배율 조절"
        title="버튼 또는 두 손가락 제스처로 확대·축소"
        className="absolute right-2 top-2 z-30 flex items-center gap-1 rounded-xl border border-white/10 bg-slate-950/85 p-1 text-xs font-semibold text-white shadow-lg backdrop-blur sm:right-3 sm:top-3 sm:p-1.5"
      >
        <button
          type="button"
          onClick={() => setZoom((current) => Math.max(0.6, current - 0.2))}
          disabled={zoom <= 0.6}
          aria-label="축소"
          className="inline-flex h-9 w-9 items-center justify-center rounded-lg text-base transition hover:bg-white/10 disabled:opacity-30"
        >
          −
        </button>
        <span className="w-12 text-center text-[11px] text-cyan-100">
          {Math.round(renderScale * 100)}%
        </span>
        <button
          type="button"
          onClick={() => setZoom((current) => Math.min(2, current + 0.2))}
          disabled={zoom >= 2}
          aria-label="확대"
          className="inline-flex h-9 w-9 items-center justify-center rounded-lg text-base transition hover:bg-white/10 disabled:opacity-30"
        >
          +
        </button>
        <button
          type="button"
          onClick={() => {
            setZoom(1);
          }}
          className="min-h-9 rounded-lg border border-white/15 px-2 py-1.5 text-[10px] text-white/80 transition hover:bg-white/10 sm:px-2.5 sm:text-[11px]"
        >
          <span className="sm:hidden">맞춤</span>
          <span className="hidden sm:inline">화면 맞춤</span>
        </button>
      </div>

      <div className="pointer-events-none absolute bottom-2 left-2 z-30 max-w-[calc(100%-1rem)] truncate rounded-full border border-white/10 bg-slate-950/75 px-2.5 py-1.5 text-[10px] font-medium text-cyan-100/80 backdrop-blur sm:bottom-3 sm:left-3 sm:px-3">
        {layout.edges.length}개 브랜치 · {comments.length}개 코멘트
        {commentsLoading ? " · 불러오는 중" : ""}
        {positionsLoading ? " · 위치 불러오는 중" : ""}
      </div>

      {commentError && (
        <div
          role="alert"
          className="absolute inset-x-2 bottom-2 z-[70] flex items-center gap-3 rounded-xl border border-rose-300/30 bg-rose-950/95 px-3 py-3 text-xs text-rose-100 shadow-2xl sm:inset-x-auto sm:bottom-3 sm:left-1/2 sm:max-w-[min(560px,80%)] sm:-translate-x-1/2 sm:px-4"
        >
          <span className="min-w-0 flex-1 break-words">{commentError}</span>
          <button
            type="button"
            onClick={() => setCommentError(null)}
            aria-label="오류 닫기"
            className="text-base text-white/70 hover:text-white"
          >
            ×
          </button>
        </div>
      )}

      <div
        className="absolute left-1/2 top-1/2 origin-center rounded-xl"
        style={{
          width: layout.width,
          height: layout.height,
          transform: `translate(-50%, -50%) scale(${renderScale})`,
          backgroundImage:
            "radial-gradient(circle at 1px 1px, rgba(125,211,252,0.16) 1px, transparent 0)",
          backgroundSize: "22px 22px",
        }}
      >
        <svg
          className="pointer-events-none absolute inset-0 z-10 overflow-visible"
          width={layout.width}
          height={layout.height}
          aria-hidden="true"
        >
          {layout.edges.map(({ fromId, toId }) => {
            const from = positions[fromId];
            const to = positions[toId];
            if (!from || !to) return null;
            const connection = connectionGeometry(from, to);

            return (
              <g key={`${fromId}-${toId}`}>
                <path
                  d={connection.path}
                  fill="none"
                  stroke="#155e75"
                  strokeWidth="8"
                  strokeLinecap="round"
                  opacity="0.55"
                  vectorEffect="non-scaling-stroke"
                />
                <path
                  d={connection.path}
                  fill="none"
                  stroke="#67e8f9"
                  strokeWidth="3.25"
                  strokeLinecap="round"
                  className="drop-shadow-[0_0_5px_rgba(34,211,238,0.7)]"
                  vectorEffect="non-scaling-stroke"
                />
                <circle
                  cx={connection.startX}
                  cy={connection.startY}
                  r="4"
                  fill="#a5f3fc"
                  stroke="#164e63"
                  strokeWidth="2"
                  vectorEffect="non-scaling-stroke"
                />
                <circle
                  cx={connection.endX}
                  cy={connection.endY}
                  r="4"
                  fill="#5eead4"
                  stroke="#134e4a"
                  strokeWidth="2"
                  vectorEffect="non-scaling-stroke"
                />
              </g>
            );
          })}

          {comments.map((comment) => {
            const from = positions[comment.thread_id];
            if (!from) return null;
            const connection = commentConnectionGeometry(from, {
              x: comment.position_x,
              y: comment.position_y,
            });
            return (
              <g key={`comment-line-${comment.id}`}>
                <path
                  d={connection.path}
                  fill="none"
                  stroke="#92400e"
                  strokeWidth="6"
                  strokeLinecap="round"
                  opacity="0.45"
                  vectorEffect="non-scaling-stroke"
                />
                <path
                  d={connection.path}
                  fill="none"
                  stroke="#fbbf24"
                  strokeWidth="2.5"
                  strokeLinecap="round"
                  strokeDasharray="5 4"
                  className="drop-shadow-[0_0_4px_rgba(251,191,36,0.65)]"
                  vectorEffect="non-scaling-stroke"
                />
                <circle
                  cx={connection.startX}
                  cy={connection.startY}
                  r="3.5"
                  fill="#fde68a"
                  stroke="#78350f"
                  strokeWidth="2"
                  vectorEffect="non-scaling-stroke"
                />
              </g>
            );
          })}
        </svg>

        {layout.nodes.map(({ node, depth }) => {
          const position = positions[node.id];
          if (!position) return null;
          const isRoot = depth === 0;

          return (
            <div
              key={node.id}
              role="treeitem"
              aria-selected="false"
              aria-disabled={node.is_deleted || undefined}
              className={`absolute z-20 ${node.is_deleted ? "opacity-40 saturate-50" : ""}`}
              style={{
                left: position.x,
                top: position.y,
                width: NODE_WIDTH,
                height: NODE_HEIGHT,
                pointerEvents: "auto",
              }}
            >
              <button
                type="button"
                onPointerDown={(event) => startNodeDrag(event, node.id)}
                onPointerMove={moveNodeDrag}
                onPointerUp={(event) => void finishNodeDrag(event)}
                onPointerCancel={(event) => void finishNodeDrag(event)}
                onClick={() => {
                  if (suppressCanvasClickRef.current) return;
                  if (ignoreNodeClickRef.current === node.id) return;
                  if (node.is_deleted) return;
                  onSelect(node.id);
                }}
                className={`flex h-full w-full cursor-grab items-center gap-2 rounded-xl border px-2.5 text-left shadow-xl transition-[border-color,background-color,box-shadow] active:cursor-grabbing focus:outline-none focus:ring-2 focus:ring-cyan-300 ${
                  isRoot
                    ? "border-fuchsia-300/60 bg-gradient-to-br from-indigo-900/95 to-fuchsia-950/95 shadow-fuchsia-950/40"
                    : "border-cyan-300/35 bg-gradient-to-br from-slate-900/95 to-cyan-950/90 shadow-cyan-950/35 hover:border-cyan-200/75"
                }`}
                style={{ touchAction: "none" }}
                title={
                  node.is_deleted
                    ? `${node.title || "제목 없는 스레드"} · 삭제된 중간 노드`
                    : `${node.title || "제목 없는 스레드"} · 드래그해서 이동`
                }
              >
                <span
                  className={`h-2.5 w-2.5 shrink-0 rounded-full shadow-[0_0_12px_currentColor] ${
                    isRoot
                      ? "bg-fuchsia-300 text-fuchsia-300"
                      : "bg-cyan-300 text-cyan-300"
                  }`}
                />
                <span className="min-w-0">
                  <span className="block truncate text-xs font-semibold text-white">
                    {nodeTitle(node.title)}
                  </span>
                  <span className="mt-0.5 block text-[8px] font-semibold uppercase tracking-[0.14em] text-white/45">
                    {node.is_deleted
                      ? "삭제된 브랜치"
                      : isRoot
                        ? "루트 노드"
                        : `브랜치 · ${depth}단계`}
                  </span>
                </span>
              </button>
              {!node.is_deleted && (
                <button
                  type="button"
                  aria-label={`${node.title || "제목 없는 스레드"}에 코멘트 추가`}
                  title="코멘트 추가"
                  onPointerDown={(event) => event.stopPropagation()}
                  onClick={(event) => {
                    event.stopPropagation();
                    setCreateTargetId(node.id);
                    setCreateText("");
                    setSelectedCommentId(null);
                  }}
                  className="absolute -right-1.5 -top-1.5 z-30 flex h-5 min-w-5 items-center justify-center rounded-full border border-sky-100/60 bg-gradient-to-br from-sky-200/80 via-cyan-300/70 to-blue-400/75 px-1 text-xs font-bold leading-none text-sky-950 shadow-md shadow-sky-950/20 backdrop-blur transition hover:scale-105 hover:from-sky-100/90 hover:to-cyan-300/85 focus:outline-none focus:ring-2 focus:ring-sky-100/70"
                >
                  +
                </button>
              )}
              {node.can_manage && !node.is_deleted && onDelete && (
                <button
                  type="button"
                  aria-label={`${node.title || "제목 없는 스레드"} 삭제`}
                  title={isRoot ? "폴더와 전체 브랜치 삭제" : "브랜치 스레드 삭제"}
                  onPointerDown={(event) => event.stopPropagation()}
                  onClick={(event) => {
                    event.stopPropagation();
                    setDeleteTarget(node);
                  }}
                  className="absolute -left-1.5 -top-1.5 z-30 flex h-5 w-5 items-center justify-center rounded-full border border-rose-200/45 bg-gradient-to-br from-rose-300/85 to-red-500/80 text-rose-950 shadow-md backdrop-blur transition hover:scale-105 hover:from-rose-200 hover:to-red-400 focus:outline-none focus:ring-2 focus:ring-rose-100/70"
                >
                  <Trash2 size={10} strokeWidth={2.5} />
                </button>
              )}
            </div>
          );
        })}

        {comments.map((comment) => {
          const isSelected = selectedCommentId === comment.id;
          const isMoving = busyAction === `move:${comment.id}`;
          return (
            <button
              key={comment.id}
              type="button"
              aria-label="코멘트 열기"
              aria-expanded={isSelected}
              onPointerDown={(event) => startCommentDrag(event, comment)}
              onPointerMove={moveCommentDrag}
              onPointerUp={(event) => void finishCommentDrag(event)}
              onPointerCancel={(event) => void finishCommentDrag(event)}
              onClick={(event) => {
                event.stopPropagation();
                if (suppressCanvasClickRef.current) return;
                if (ignoreCommentClickRef.current === comment.id) return;
                setSelectedCommentId((current) =>
                  current === comment.id ? null : comment.id,
                );
                setEditingCommentId(null);
              }}
              className={`absolute z-30 flex h-[18px] w-[18px] items-center justify-center rounded-full border-2 shadow-[0_0_14px_rgba(251,191,36,0.9)] transition ${
                comment.can_edit
                  ? "cursor-grab active:cursor-grabbing"
                  : "cursor-pointer"
              } ${
                isSelected
                  ? "border-white bg-amber-200 ring-4 ring-amber-300/25"
                  : "border-amber-100 bg-amber-400 hover:scale-125 hover:bg-amber-200"
              }`}
              style={{
                left: comment.position_x - COMMENT_RADIUS,
                top: comment.position_y - COMMENT_RADIUS,
                touchAction: "none",
              }}
            >
              <span
                className={`h-1.5 w-1.5 rounded-full bg-amber-900 ${
                  isMoving ? "animate-pulse" : ""
                }`}
              />
            </button>
          );
        })}

        {selectedComment && (
          <section
            role="dialog"
            aria-label="노드 코멘트"
            className="absolute z-50 w-[230px] rounded-2xl border border-amber-200/35 bg-slate-950/95 p-3 text-white shadow-2xl shadow-amber-950/50 backdrop-blur"
            style={{
              left: selectedCommentPanelPosition?.left,
              top: selectedCommentPanelPosition?.top,
              transform: `scale(${1 / renderScale})`,
              transformOrigin: "left top",
            }}
            onPointerDown={(event) => event.stopPropagation()}
          >
            <div className="flex items-center justify-between">
              {selectedComment.can_edit ? (
                <button
                  type="button"
                  onClick={() => void removeComment(selectedComment.id)}
                  disabled={Boolean(busyAction)}
                  className="rounded-md px-1.5 py-1 text-[10px] font-semibold text-rose-300 transition hover:bg-rose-400/10 disabled:opacity-40"
                >
                  {busyAction === `delete:${selectedComment.id}`
                    ? "삭제 중"
                    : "삭제"}
                </button>
              ) : (
                <span className="w-8" aria-hidden="true" />
              )}
              <span className="text-[9px] font-bold uppercase tracking-[0.18em] text-amber-200/70">
                코멘트
              </span>
              <button
                type="button"
                aria-label="코멘트 창 닫기"
                onClick={() => {
                  setSelectedCommentId(null);
                  setEditingCommentId(null);
                }}
                className="flex h-6 w-6 items-center justify-center rounded-md text-lg leading-none text-white/60 transition hover:bg-white/10 hover:text-white"
              >
                ×
              </button>
            </div>

            <p className="mt-2 truncate border-b border-white/10 pb-2 text-[10px] font-semibold text-sky-200/80">
              작성자 · {selectedComment.author_id}
            </p>

            {editingCommentId === selectedComment.id ? (
              <>
                <textarea
                  value={editingText}
                  onChange={(event) => setEditingText(event.target.value)}
                  maxLength={4000}
                  autoFocus
                  className="mt-2 h-24 w-full resize-none overflow-y-auto rounded-xl border border-amber-200/30 bg-black/25 px-3 py-2 text-xs leading-5 text-white outline-none placeholder:text-white/30 focus:border-amber-200/70 [scrollbar-color:rgba(251,191,36,0.45)_rgba(15,23,42,0.5)] [scrollbar-width:thin]"
                />
                <div className="mt-3 flex justify-center">
                  <button
                    type="button"
                    onClick={() =>
                      void submitEditedComment(selectedComment.id)
                    }
                    disabled={!editingText.trim() || Boolean(busyAction)}
                    className="rounded-lg bg-amber-300 px-5 py-2 text-[11px] font-bold text-amber-950 transition hover:bg-amber-200 disabled:cursor-not-allowed disabled:opacity-45"
                  >
                    {busyAction === `edit:${selectedComment.id}`
                      ? "저장 중..."
                      : "완료"}
                  </button>
                </div>
              </>
            ) : (
              <>
                <p className="mt-2 max-h-28 overflow-y-auto whitespace-pre-wrap break-words rounded-xl bg-white/[0.04] px-3 py-2.5 text-xs leading-5 text-amber-50 [scrollbar-color:rgba(251,191,36,0.45)_rgba(15,23,42,0.5)] [scrollbar-width:thin]">
                  {selectedComment.content}
                </p>
                {selectedComment.can_edit && (
                  <div className="mt-3 flex justify-end">
                    <button
                      type="button"
                      onClick={() => {
                        setEditingCommentId(selectedComment.id);
                        setEditingText(selectedComment.content);
                      }}
                      disabled={Boolean(busyAction)}
                      className="rounded-lg border border-amber-200/30 px-3 py-1.5 text-[10px] font-semibold text-amber-100 transition hover:bg-amber-300/10 disabled:opacity-40"
                    >
                      수정
                    </button>
                  </div>
                )}
              </>
            )}
          </section>
        )}
      </div>

      {createTargetId && (
        <div
          className="absolute inset-0 z-[80] flex items-center justify-center overflow-y-auto bg-slate-950/65 p-3 backdrop-blur-sm sm:p-4"
          role="presentation"
        >
          <section
            role="dialog"
            aria-modal="true"
            aria-labelledby="branch-comment-title"
            className="my-auto max-h-[calc(100%-1rem)] w-full max-w-md overflow-y-auto rounded-2xl border border-amber-200/25 bg-[#111b2e] p-4 shadow-2xl shadow-black/60 sm:p-5"
          >
            <h2
              id="branch-comment-title"
              className="text-base font-bold text-white"
            >
              노드 코멘트 작성
            </h2>
            <p className="mt-1 text-xs text-amber-100/65">
              작성한 코멘트는 이 스레드 노드에 연결되어 저장됩니다.
            </p>
            <textarea
              value={createText}
              onChange={(event) => setCreateText(event.target.value)}
              maxLength={4000}
              autoFocus
              placeholder="코멘트를 입력하세요"
              className="mt-4 h-36 w-full resize-none overflow-y-auto rounded-xl border border-white/15 bg-slate-950/50 px-4 py-3 text-sm leading-6 text-white outline-none placeholder:text-white/30 focus:border-amber-200/60 [scrollbar-color:rgba(125,211,252,0.45)_rgba(15,23,42,0.5)] [scrollbar-width:thin]"
            />
            <div className="mt-5 flex items-center justify-between">
              <button
                type="button"
                onClick={() => {
                  setCreateTargetId(null);
                  setCreateText("");
                }}
                disabled={busyAction === "create"}
                className="rounded-lg border border-white/15 px-4 py-2 text-xs font-semibold text-white/75 transition hover:bg-white/10 disabled:opacity-40"
              >
                취소
              </button>
              <button
                type="button"
                onClick={() => void submitNewComment()}
                disabled={!createText.trim() || busyAction === "create"}
                className="rounded-lg bg-amber-300 px-5 py-2 text-xs font-bold text-amber-950 transition hover:bg-amber-200 disabled:cursor-not-allowed disabled:opacity-45"
              >
                {busyAction === "create" ? "저장 중..." : "완료"}
              </button>
            </div>
          </section>
        </div>
      )}

      <DeleteConfirmModal
        isOpen={Boolean(deleteTarget)}
        title={
          deleteTarget?.id === root.id
            ? "브랜치 폴더 전체를 삭제하시겠습니까?"
            : "이 브랜치 스레드를 삭제하시겠습니까?"
        }
        description={
          deleteTarget?.id === root.id
            ? "루트 스레드와 연결된 전체 브랜치가 함께 삭제됩니다."
            : "하위 브랜치가 있으면 노드가 비활성화되고, 말단 노드면 완전히 삭제됩니다."
        }
        onCancel={() => setDeleteTarget(null)}
        onConfirm={async () => {
          if (deleteTarget) await onDelete?.(deleteTarget);
          setDeleteTarget(null);
        }}
      />
    </div>
  );
}
