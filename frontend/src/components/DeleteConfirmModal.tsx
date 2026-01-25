"use client";

type Props = {
  isOpen: boolean;
  title?: string;
  description?: string;
  onCancel: () => void;
  onConfirm: () => void;
};

export function DeleteConfirmModal({
  isOpen,
  title = "삭제하시겠습니까?",
  description = "이 작업은 되돌릴 수 없습니다.",
  onCancel,
  onConfirm,
}: Props) {
  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 backdrop-blur">
      <div className="w-full max-w-sm rounded-2xl bg-white p-6 shadow-2xl">
        <h2 className="text-lg font-bold text-slate-900">{title}</h2>
        <p className="mt-2 text-sm text-slate-600">{description}</p>

        <div className="mt-6 flex justify-end gap-2">
          <button
            onClick={onCancel}
            className="rounded-lg px-4 py-2 text-sm font-semibold text-slate-600 hover:bg-slate-100"
          >
            취소
          </button>
          <button
            onClick={onConfirm}
            className="rounded-lg bg-red-600 px-4 py-2 text-sm font-semibold text-white shadow-sm hover:bg-red-700"
          >
            확인
          </button>
        </div>
      </div>
    </div>
  );
}
