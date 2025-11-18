// frontend/src/app/page.tsx
import { redirect } from "next/navigation";

export default function Home() {
  // 사이트 첫 진입 시 /login 으로 보내기
  redirect("/login");
}
