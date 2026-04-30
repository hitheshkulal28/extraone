import React, { useState } from "react";
import { useNavigate } from "react-router-dom";
import { auth } from "../firebase";
import {
  signInWithEmailAndPassword,
  GoogleAuthProvider,
  GithubAuthProvider,
  signInWithPopup,
} from "firebase/auth";

const Login = () => {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");

  const navigate = useNavigate();

  const handleLogin = async (e) => {
    e.preventDefault();
    try {
      const res = await signInWithEmailAndPassword(auth, email, password);
      const token = await res.user.getIdToken();
      sessionStorage.setItem("vantixAdminToken", token);
      navigate("/");
    } catch (err) {
      setError(err.code);
    }
  };

  const googleLogin = async () => {
    try {
      const provider = new GoogleAuthProvider();
      const result = await signInWithPopup(auth, provider);
      const token = await result.user.getIdToken();
      sessionStorage.setItem("vantixAdminToken", token);
      navigate("/");
    } catch (err) {
      setError(err.code);
    }
  };

  const githubLogin = async () => {
    try {
      const provider = new GithubAuthProvider();
      const result = await signInWithPopup(auth, provider);
      const token = await result.user.getIdToken();
      sessionStorage.setItem("vantixAdminToken", token);
      navigate("/");
    } catch (err) {
      setError(err.code);
    }
  };

  return (
    <div style={{ height: "100vh", display: "flex", alignItems: "center", justifyContent: "center" }}>
      <form onSubmit={handleLogin} style={{ padding: 40, width: 350 }}>
        <h2>Vantix Admin Login</h2>

        {error && <p style={{ color: "red" }}>{error}</p>}

        <input
          type="email"
          placeholder="Email"
          value={email}
          onChange={(e) => setEmail(e.target.value)}
        />

        <input
          type="password"
          placeholder="Password"
          value={password}
          onChange={(e) => setPassword(e.target.value)}
        />

        <button type="submit">Login</button>

        <hr />

        <button type="button" onClick={googleLogin}>
          Continue with Google
        </button>

        <button type="button" onClick={githubLogin}>
          Continue with GitHub
        </button>
      </form>
    </div>
  );
};

export default Login;