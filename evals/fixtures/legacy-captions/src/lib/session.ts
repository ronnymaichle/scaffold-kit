import { getAuth } from "firebase-admin/auth";
import "./firebase-admin";

export async function getUserFromSession(request: Request) {
  const token = request.headers.get("authorization")?.replace("Bearer ", "");
  if (!token) return null;
  try {
    return await getAuth().verifyIdToken(token);
  } catch {
    return null;
  }
}
