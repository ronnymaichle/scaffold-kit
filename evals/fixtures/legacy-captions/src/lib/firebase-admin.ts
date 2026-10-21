import { cert, getApps, initializeApp } from "firebase-admin/app";
import { getFirestore } from "firebase-admin/firestore";

const app = getApps()[0] ?? initializeApp({ credential: cert(JSON.parse(process.env.FIREBASE_SERVICE_ACCOUNT ?? "{}")) });

export const db = getFirestore(app);
