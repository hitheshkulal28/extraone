// Vantix Extension — Firebase Configuration (Compat Mode)

const firebaseConfig = {
    apiKey: "AIzaSyDajd1mzoWG1bz2_dlIQs5prPGms7FU8Jg",
    authDomain: "gen-lang-client-0119077364.firebaseapp.com",
    projectId: "gen-lang-client-0119077364",
    storageBucket: "gen-lang-client-0119077364.firebasestorage.app",
    messagingSenderId: "1204185065",
    appId: "1:1204185065:web:e3b9f9d1455417ab954d78"
};

// Use the global 'firebase' object provided by the local scripts in popup.html
const app = window.firebase.initializeApp(firebaseConfig);
export const auth = window.firebase.auth();

export const GoogleAuthProvider = window.firebase.auth.GoogleAuthProvider;
export const GithubAuthProvider = window.firebase.auth.GithubAuthProvider;
