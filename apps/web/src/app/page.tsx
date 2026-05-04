import { redirect } from "next/navigation";
import { fetchServerSession } from "@/lib/server-auth";

export default async function Home() {
  const session = await fetchServerSession();
  redirect(session.authenticated ? "/tasks" : "/login");
}
