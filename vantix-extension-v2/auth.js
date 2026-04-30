// Vantix Extension — Auth Helper Script (Redirect Flow for MV3)
const firebaseConfig = {
    apiKey: "AIzaSyDajd1mzoWG1bz2_dlIQs5prPGms7FU8Jg",
    authDomain: "gen-lang-client-0119077364.firebaseapp.com",
    projectId: "gen-lang-client-0119077364",
    storageBucket: "gen-lang-client-0119077364.firebasestorage.app",
    messagingSenderId: "1204185065",
    appId: "1:1204185065:web:e3b9f9d1455417ab954d78"
};

async function handleLogin() {
    const statusEl = document.getElementById('status');
    const urlParams = new URLSearchParams(window.location.search);
    const providerType = urlParams.get('provider');

    try {
        if (!window.firebase.apps.length) {
            window.firebase.initializeApp(firebaseConfig);
        }
        const auth = window.firebase.auth();
        
        // 1. Check if we are returning from a redirect
        const result = await auth.getRedirectResult();
        
        if (result && result.user) {
            // WE JUST LOGGED IN!
            const token = await result.user.getIdToken();
            statusEl.textContent = "Login Successful! Syncing...";
            
            chrome.storage.local.set({
                vantixToken: token,
                vantixEmail: result.user.email
            }, () => {
                setTimeout(() => window.close(), 1000);
            });
            return;
        }

        // 2. If not returning from redirect, start the flow
        let provider;
        if (providerType === 'google') {
            provider = new window.firebase.auth.GoogleAuthProvider();
            statusEl.textContent = "Redirecting to Google...";
        } else if (providerType === 'github') {
            provider = new window.firebase.auth.GithubAuthProvider();
            statusEl.textContent = "Redirecting to GitHub...";
        } else {
            return;
        }

        // Use Redirect instead of Popup for better MV3 compatibility
        await auth.signInWithRedirect(provider);

    } catch (err) {
        console.error("Auth Error:", err);
        statusEl.style.color = "#fc8181";
        statusEl.textContent = `Error: ${err.message || err.code}`;
    }
}

handleLogin();
