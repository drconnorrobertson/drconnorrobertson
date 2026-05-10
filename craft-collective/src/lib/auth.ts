import { cookies } from "next/headers";
import { env } from "./env";

const COOKIE_NAME = "cc_auth";

export async function isAuthed(): Promise<boolean> {
  const password = env.appPassword;
  if (!password) return true; // auth disabled
  const jar = await cookies();
  return jar.get(COOKIE_NAME)?.value === password;
}

export async function signIn(password: string): Promise<boolean> {
  const expected = env.appPassword;
  if (!expected) return true;
  if (password !== expected) return false;
  const jar = await cookies();
  jar.set(COOKIE_NAME, expected, {
    httpOnly: true,
    sameSite: "lax",
    secure: process.env.NODE_ENV === "production",
    path: "/",
    maxAge: 60 * 60 * 24 * 7,
  });
  return true;
}

export async function signOut(): Promise<void> {
  const jar = await cookies();
  jar.delete(COOKIE_NAME);
}
