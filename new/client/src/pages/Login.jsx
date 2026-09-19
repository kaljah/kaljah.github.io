import React, { useState, useEffect, useRef } from "react";
import { useAuth } from "../context/AuthContext";
import { useNavigate } from "react-router-dom";
import { motion, AnimatePresence } from "framer-motion";
import api from "../api";
import "./Login.css";

const GhgCloud = () => {
  const cloud1Ref = useRef(null);
  const cloud2Ref = useRef(null);

  // Use refs for animation coordinates to avoid React re-renders on mouse move (60fps performance)
  const target = useRef({ x: -1000, y: -1000 });
  const pos1 = useRef({ x: -1000, y: -1000 });
  const pos2 = useRef({ x: -1000, y: -1000 });

  useEffect(() => {
    const handleMouseMove = (e) => {
      target.current = { x: e.clientX, y: e.clientY };
    };
    window.addEventListener("mousemove", handleMouseMove);

    // Initialize position to center if mouse hasn't moved yet
    setTimeout(() => {
      if (target.current.x === -1000) {
        target.current = {
          x: window.innerWidth / 2,
          y: window.innerHeight / 2,
        };
        pos1.current = { ...target.current };
        pos2.current = { ...target.current };
      }
    }, 100);

    return () => window.removeEventListener("mousemove", handleMouseMove);
  }, []);

  useEffect(() => {
    let animationFrameId;
    const animate = () => {
      // Cloud 1 (CO2 - Orange/Grey) follows quickly
      pos1.current.x += (target.current.x - pos1.current.x) * 0.06;
      pos1.current.y += (target.current.y - pos1.current.y) * 0.06;

      // Cloud 2 (Methane - Green) follows lazily, creating a mixing effect
      pos2.current.x += (target.current.x - pos2.current.x) * 0.02;
      pos2.current.y += (target.current.y - pos2.current.y) * 0.02;

      if (cloud1Ref.current) {
        cloud1Ref.current.style.transform = `translate(calc(${pos1.current.x}px - 50%), calc(${pos1.current.y}px - 50%))`;
      }
      if (cloud2Ref.current) {
        cloud2Ref.current.style.transform = `translate(calc(${pos2.current.x}px - 50%), calc(${pos2.current.y}px - 50%))`;
      }
      animationFrameId = requestAnimationFrame(animate);
    };
    animate();
    return () => cancelAnimationFrame(animationFrameId);
  }, []);

  return (
    <div className="ghg-cloud-container">
      <div className="ghg-cloud ch4-cloud" ref={cloud2Ref}></div>
      <div className="ghg-cloud co2-cloud" ref={cloud1Ref}></div>
      <div className="ghg-noise-overlay"></div>
    </div>
  );
};

const Login = () => {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");

  // Forgot password modal state
  const [showForgotModal, setShowForgotModal] = useState(false);
  const [forgotEmail, setForgotEmail] = useState("");
  const [forgotLoading, setForgotLoading] = useState(false);
  const [forgotMsg, setForgotMsg] = useState({ text: "", type: "" });

  // Intro video state
  const [showIntro, setShowIntro] = useState(true);
  const [introFading, setIntroFading] = useState(false);

  const { login, sessionExpired, setSessionExpired } = useAuth();
  const navigate = useNavigate();

  const handleIntroEnd = () => {
    setIntroFading(true);
    setTimeout(() => setShowIntro(false), 800); // Matches CSS transition duration
  };

  const handleLogin = async (e) => {
    e.preventDefault();
    setError("");
    if (sessionExpired) setSessionExpired(false);
    try {
      await login(email, password);
      navigate("/");
    } catch (err) {
      setError(err.response?.data?.error || "Invalid credentials");
    }
  };

  const handleForgotPassword = async (e) => {
    e.preventDefault();
    if (!forgotEmail.trim()) {
      setForgotMsg({ text: "Please enter your email address.", type: "error" });
      return;
    }
    setForgotLoading(true);
    setForgotMsg({ text: "", type: "" });
    try {
      const res = await api.post("/auth/forgot-password", { email: forgotEmail.trim() });
      setForgotMsg({
        text: res.data.message || "Password reset request submitted. Your IT Administrator has been notified.",
        type: "success",
      });
      setTimeout(() => {
        // Clear input on success
        setForgotEmail("");
      }, 1000);
    } catch (err) {
      setForgotMsg({
        text: err.response?.data?.error || "Failed to submit request. Please try again later.",
        type: "error",
      });
    } finally {
      setForgotLoading(false);
    }
  };

  return (
    <div className="login-body">
      {showIntro && (
        <div
          className={`login-intro-overlay ${introFading ? "intro-fade-out" : ""}`}
        >
          <video
            src="/login_animation.mp4"
            autoPlay
            muted
            playsInline
            onEnded={handleIntroEnd}
            className="login-intro-video"
          />
          <button className="skip-intro-btn" onClick={handleIntroEnd}>
            Skip Intro
          </button>
        </div>
      )}

      <GhgCloud />

      <motion.div
        className="login-container glass-panel"
        initial={{ opacity: 0, y: 30 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.6, ease: "easeOut" }}
      >
        {/* Welcome Text */}
        <div className="login-header">
          <h2>Welcome Back</h2>
          <p>Sign in to your GHG Reporting Platform</p>
        </div>

        {/* Inactivity Session Expiration Banner */}
        {sessionExpired && (
          <div
            className="session-expired-alert"
            style={{
              display: "flex",
              alignItems: "center",
              gap: "10px",
              padding: "12px 14px",
              background: "#fffbeb",
              border: "1px solid #fde68a",
              borderRadius: "10px",
              color: "#92400e",
              fontSize: "0.85rem",
              marginBottom: "16px",
              lineHeight: 1.4,
            }}
          >
            <svg
              width="18"
              height="18"
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              strokeWidth="2"
              strokeLinecap="round"
              strokeLinejoin="round"
              style={{ flexShrink: 0, color: "#d97706" }}
            >
              <circle cx="12" cy="12" r="10"></circle>
              <line x1="12" y1="8" x2="12" y2="12"></line>
              <line x1="12" y1="16" x2="12.01" y2="16"></line>
            </svg>
            <span>
              Your session timed out after 10 minutes of inactivity. Please sign in again to resume your work.
            </span>
          </div>
        )}

        {/* Error Message */}
        {error && (
          <div className="error-message">
            <svg
              width="18"
              height="18"
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              strokeWidth="2"
            >
              <circle cx="12" cy="12" r="10"></circle>
              <line x1="12" y1="8" x2="12" y2="12"></line>
              <line x1="12" y1="16" x2="12.01" y2="16"></line>
            </svg>
            {error}
          </div>
        )}

        {/* Login Form */}
        <motion.form
          onSubmit={handleLogin}
          className="login-form"
          initial="hidden"
          animate="visible"
          variants={{
            hidden: { opacity: 0 },
            visible: {
              opacity: 1,
              transition: { staggerChildren: 0.1, delayChildren: 0.2 },
            },
          }}
        >
          <motion.div
            className="form-group"
            variants={{
              hidden: { opacity: 0, y: 20 },
              visible: { opacity: 1, y: 0 },
            }}
          >
            <div className="input-wrapper">
              <span className="input-icon">
                <svg
                  width="18"
                  height="18"
                  viewBox="0 0 24 24"
                  fill="none"
                  stroke="currentColor"
                  strokeWidth="2"
                  strokeLinecap="round"
                  strokeLinejoin="round"
                >
                  <path d="M4 4h16c1.1 0 2 .9 2 2v12c0 1.1-.9 2-2 2H4c-1.1 0-2-.9-2-2V6c0-1.1.9-2 2-2z"></path>
                  <polyline points="22,6 12,13 2,6"></polyline>
                </svg>
              </span>
              <input
                type="text"
                className="form-control"
                required
                placeholder="Email Address"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                autoComplete="username"
              />
            </div>
          </motion.div>

          <motion.div
            className="form-group"
            variants={{
              hidden: { opacity: 0, y: 20 },
              visible: { opacity: 1, y: 0 },
            }}
          >
            <div className="input-wrapper">
              <span className="input-icon">
                <svg
                  width="18"
                  height="18"
                  viewBox="0 0 24 24"
                  fill="none"
                  stroke="currentColor"
                  strokeWidth="2"
                  strokeLinecap="round"
                  strokeLinejoin="round"
                >
                  <rect
                    x="3"
                    y="11"
                    width="18"
                    height="11"
                    rx="2"
                    ry="2"
                  ></rect>
                  <path d="M7 11V7a5 5 0 0 1 10 0v4"></path>
                </svg>
              </span>
              <input
                type="password"
                className="form-control"
                required
                placeholder="Password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                autoComplete="current-password"
              />
            </div>
          </motion.div>

          <div className="login-actions-row">
            <button
              type="button"
              className="forgot-password-link"
              onClick={() => {
                setForgotEmail(email || "");
                setForgotMsg({ text: "", type: "" });
                setShowForgotModal(true);
              }}
            >
              Forgot password?
            </button>
          </div>

          <motion.button
            type="submit"
            className="btn-primary"
            variants={{
              hidden: { opacity: 0, y: 20 },
              visible: { opacity: 1, y: 0 },
            }}
            whileHover={{ scale: 1.02 }}
            whileTap={{ scale: 0.98 }}
          >
            Sign In
          </motion.button>
        </motion.form>

        {/* Footer / Compliance */}
        <div className="login-footer">
          <div className="mini-badges">
            <span className="badge">API Compliant</span>
            <span className="badge">ISO 14064 Ready</span>
            <span className="badge">SOC2 Secured</span>
          </div>
          <p>© {new Date().getFullYear()} Carbon Tech. All rights reserved.</p>
        </div>
      </motion.div>

      {/* Forgot Password Modal */}
      <AnimatePresence>
        {showForgotModal && (
          <div className="forgot-modal-overlay" onClick={() => setShowForgotModal(false)}>
            <motion.div
              className="forgot-modal-content"
              onClick={(e) => e.stopPropagation()}
              initial={{ opacity: 0, scale: 0.95, y: 15 }}
              animate={{ opacity: 1, scale: 1, y: 0 }}
              exit={{ opacity: 0, scale: 0.95, y: 15 }}
              transition={{ duration: 0.2 }}
            >
              <div className="forgot-modal-header">
                <h3>Reset Your Password</h3>
                <p>
                  Enter your account email. A notification will be dispatched to your IT Administrator to reset your credentials.
                </p>
              </div>

              {forgotMsg.text && (
                <div className={`forgot-status-msg ${forgotMsg.type}`}>
                  {forgotMsg.text}
                </div>
              )}

              <form onSubmit={handleForgotPassword}>
                <div className="form-group" style={{ marginBottom: '16px' }}>
                  <div className="input-wrapper">
                    <span className="input-icon">
                      <svg
                        width="18"
                        height="18"
                        viewBox="0 0 24 24"
                        fill="none"
                        stroke="currentColor"
                        strokeWidth="2"
                        strokeLinecap="round"
                        strokeLinejoin="round"
                      >
                        <path d="M4 4h16c1.1 0 2 .9 2 2v12c0 1.1-.9 2-2 2H4c-1.1 0-2-.9-2-2V6c0-1.1.9-2 2-2z"></path>
                        <polyline points="22,6 12,13 2,6"></polyline>
                      </svg>
                    </span>
                    <input
                      type="email"
                      className="form-control"
                      required
                      placeholder="Enter registered email"
                      value={forgotEmail}
                      onChange={(e) => setForgotEmail(e.target.value)}
                      autoFocus
                    />
                  </div>
                </div>

                <div className="forgot-modal-actions">
                  <button
                    type="button"
                    className="btn-secondary"
                    onClick={() => setShowForgotModal(false)}
                  >
                    Cancel
                  </button>
                  <button
                    type="submit"
                    className="btn-primary"
                    style={{ margin: 0, flex: 1.2 }}
                    disabled={forgotLoading}
                  >
                    {forgotLoading ? "Sending..." : "Notify IT Admin"}
                  </button>
                </div>
              </form>
            </motion.div>
          </div>
        )}
      </AnimatePresence>
    </div>
  );
};

export default Login;
