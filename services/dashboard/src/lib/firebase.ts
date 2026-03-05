import { initializeApp } from "firebase/app";
import {
  getAuth,
  GoogleAuthProvider,
} from "firebase/auth";

const firebaseConfig = {
  apiKey: "AIzaSyDyiL2l1sEgMRaaFmuYVpApAB2Kcdi8iMU",
  authDomain: "voxsentinel-9c7ce.firebaseapp.com",
  projectId: "voxsentinel-9c7ce",
  storageBucket: "voxsentinel-9c7ce.firebasestorage.app",
  messagingSenderId: "577749098626",
  appId: "1:577749098626:web:5da979beb487c246de149b",
  measurementId: "G-BBLRMK9KM7",
};

const app = initializeApp(firebaseConfig);
export const auth = getAuth(app);
export const googleProvider = new GoogleAuthProvider();
