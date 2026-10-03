import { Eye, EyeOff, CircleAlert, Lock } from "lucide-react";
import { Banner } from "../ui";
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
    // no continuous animation for users who prefer reduced motion
    if (window.matchMedia?.("(prefers-reduced-motion: reduce)").matches) return undefined;
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
    <div className="[position:absolute] [top:0] [left:0] [right:0] [bottom:0] [pointer-events:none]! [z-index:1] [overflow:hidden]!">
      <div className="ghg-cloud [background:radial-gradient(_circle,_rgba(16,_185,_129,_0.5)_0%,_rgba(15,_23,_42,_0.2)_50%,_transparent_70%_)]! [width:900px]! [height:900px]!" ref={cloud2Ref}></div>
      <div className="ghg-cloud [background:radial-gradient(_circle,_rgba(255,_102,_0,_0.6)_0%,_rgba(100,_116,_139,_0.3)_50%,_transparent_70%_)]!" ref={cloud1Ref}></div>
      <div className="ghg-noise-overlay"></div>
    </div>
  );
};

const Login = () => {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [showPassword, setShowPassword] = useState(false);
  const [error, setError] = useState("");

  // Forgot password modal state
  const [showForgotModal, setShowForgotModal] = useState(false);
  const [forgotEmail, setForgotEmail] = useState("");
  const [forgotLoading, setForgotLoading] = useState(false);
  const [forgotMsg, setForgotMsg] = useState({ text: "", type: "" });

  const { login, sessionExpired, setSessionExpired } = useAuth();
  const navigate = useNavigate();

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
      <GhgCloud />

      <motion.div
        className="[width:100%]! [max-width:440px]! [padding:48px]! [border-radius:var(--radius-lg)]! [position:relative]! [z-index:10]! glass-panel"
        initial={{ opacity: 0, y: 30 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.6, ease: "easeOut" }}
      >
        {/* Welcome Text */}
        <div className="[text-align:center]! [margin-bottom:32px]! [&_h2]:[font-size:var(--text-2xl)]! [&_h2]:[font-weight:800]! [&_h2]:[color:var(--text-main)]! [&_h2]:[margin-bottom:8px]! [&_h2]:[letter-spacing:-0.5px]! [&_p]:[color:var(--text-muted)]! [&_p]:[font-size:var(--text-md)]!">
          <img src={`${import.meta.env.BASE_URL}carbon_tech.svg`} alt="Carbon Tech" className="[display:block]! [width:48px]! [height:48px]! [margin:0_auto_12px]!" />
          <h2>Welcome Back</h2>
          <p>Sign in to your GHG Reporting Platform</p>
        </div>

        {/* Inactivity Session Expiration Banner */}
        {sessionExpired && (
          <Banner tone="warning" className="mb-4">
            Your session timed out after 10 minutes of inactivity. Please sign in again to resume your work.
          </Banner>
        )}

        {/* Error Message */}
        {error && (
          <div className="error-message">
            <CircleAlert size="18" strokeWidth="2" aria-hidden="true" />
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
            <div className="[position:relative]">
              <span className="input-icon [position:absolute] [left:16px] [top:50%] [transform:translateY(-50%)] [color:var(--color-ink-600)]! [transition:color_0.3s]!">
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
                className="[width:100%]! [padding:14px_16px_14px_48px]! [border:1px_solid_var(--border-light)]! [&&]:[border-radius:var(--radius-md)]! [font-size:var(--text-md)]! [color:var(--text-main)]! [transition:all_0.2s]! [background:#fafafa]! placeholder:[color:var(--color-ink-400)]! focus:[outline:none]! focus:[border-color:var(--primary)]! focus:[background:var(--color-white)]! focus:[box-shadow:0_0_0_4px_rgba(255,_102,_0,_0.1)]! [&:focus+.input-icon]:[color:var(--primary)]!"
                required
                placeholder="Email Address"
                aria-label="Email address"
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
            <div className="[position:relative]">
              <span className="input-icon [position:absolute] [left:16px] [top:50%] [transform:translateY(-50%)] [color:var(--color-ink-600)]! [transition:color_0.3s]!">
                <Lock size="18" strokeWidth="2" aria-hidden="true" />
              </span>
              <input
                type={showPassword ? "text" : "password"}
                className="[width:100%]! [padding:14px_16px_14px_48px]! [border:1px_solid_var(--border-light)]! [&&]:[border-radius:var(--radius-md)]! [font-size:var(--text-md)]! [color:var(--text-main)]! [transition:all_0.2s]! [background:#fafafa]! placeholder:[color:var(--color-ink-400)]! focus:[outline:none]! focus:[border-color:var(--primary)]! focus:[background:var(--color-white)]! focus:[box-shadow:0_0_0_4px_rgba(255,_102,_0,_0.1)]! [&:focus+.input-icon]:[color:var(--primary)]!"
                required
                placeholder="Password"
                aria-label="Password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                autoComplete="current-password"
              />
              <button
                type="button"
                className="[position:absolute] [top:50%] [right:12px] [transform:translateY(-50%)] [display:inline-flex]! [padding:6px]! [border:0]! [&&]:[border-radius:var(--radius-md)]! [background:transparent]! [color:var(--color-ink-500)]! [cursor:pointer] hover:[background:var(--color-ink-100)]! hover:[color:var(--color-ink-900)]!"
                onClick={() => setShowPassword((v) => !v)}
                aria-label={showPassword ? "Hide password" : "Show password"}
                aria-pressed={showPassword}
              >
                {showPassword ? <EyeOff size={18} aria-hidden="true" /> : <Eye size={18} aria-hidden="true" />}
              </button>
            </div>
          </motion.div>

          <div className="[display:flex]! [justify-content:flex-end] [margin-top:8px]! [margin-bottom:8px]!">
            <button
              type="button"
              className="[background:none]! [border:none]! [color:var(--primary)]! [font-size:var(--text-base)]! [font-weight:500]! [cursor:pointer] [padding:0]! [transition:color_0.2s]! hover:[color:var(--primary-hover)]! hover:[text-decoration:underline]!"
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
        <div className="[margin-top:40px]! [text-align:center]! [border-top:1px_solid_var(--border-light)]! [padding-top:24px]! [&_p]:[color:var(--text-muted)]! [&_p]:[font-size:var(--text-sm)]!">
          <div className="[display:flex]! [justify-content:center] [gap:12px] [margin-bottom:16px]!">
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
          <div className="[position:fixed] [inset:0] [background:rgba(15,_23,_42,_0.6)]! [backdrop-filter:blur(8px)] [display:flex]! [align-items:center] [justify-content:center] [z-index:1000] [padding:20px]!" onClick={() => setShowForgotModal(false)}>
            <motion.div
              className="[width:100%]! [max-width:440px]! [background:var(--color-white)]! [border-radius:var(--radius-lg)]! [padding:32px]! [box-shadow:var(--shadow-raised)]! [border:1px_solid_rgba(226,_232,_240,_0.8)]! [position:relative]"
              onClick={(e) => e.stopPropagation()}
              initial={{ opacity: 0, scale: 0.95, y: 15 }}
              animate={{ opacity: 1, scale: 1, y: 0 }}
              exit={{ opacity: 0, scale: 0.95, y: 15 }}
              transition={{ duration: 0.2 }}
            >
              <div className="[margin-bottom:20px]! [text-align:left]! [&_h3]:[font-size:var(--text-xl)]! [&_h3]:[font-weight:700]! [&_h3]:[color:var(--text-main)]! [&_h3]:[margin-bottom:6px]! [&_p]:[font-size:var(--text-base)]! [&_p]:[color:var(--text-muted)]! [&_p]:[line-height:1.4]!">
                <h3>Reset Your Password</h3>
                <p>
                  Enter your account email. A notification will be dispatched to your IT Administrator to reset your credentials.
                </p>
              </div>

              {forgotMsg.text && (
                <div className={`[padding:12px_16px]! [border-radius:var(--radius-md)]! [font-size:var(--text-base)]! [margin-bottom:18px]! [line-height:1.4]! [&.success]:[background:var(--color-green-50)]! [&.success]:[color:#065f46]! [&.success]:[border:1px_solid_#a7f3d0]! [&.error]:[background:var(--color-red-50)]! [&.error]:[color:#991b1b]! [&.error]:[border:1px_solid_#fecaca]! ${forgotMsg.type}`}>
                  {forgotMsg.text}
                </div>
              )}

              <form onSubmit={handleForgotPassword}>
                <div className="form-group mb-[16px]!">
                  <div className="[position:relative]">
                    <span className="input-icon [position:absolute] [left:16px] [top:50%] [transform:translateY(-50%)] [color:var(--color-ink-600)]! [transition:color_0.3s]!">
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
                      className="[width:100%]! [padding:14px_16px_14px_48px]! [border:1px_solid_var(--border-light)]! [&&]:[border-radius:var(--radius-md)]! [font-size:var(--text-md)]! [color:var(--text-main)]! [transition:all_0.2s]! [background:#fafafa]! placeholder:[color:var(--color-ink-400)]! focus:[outline:none]! focus:[border-color:var(--primary)]! focus:[background:var(--color-white)]! focus:[box-shadow:0_0_0_4px_rgba(255,_102,_0,_0.1)]! [&:focus+.input-icon]:[color:var(--primary)]!"
                      required
                      placeholder="Enter registered email"
                      value={forgotEmail}
                      onChange={(e) => setForgotEmail(e.target.value)}
                      autoFocus
                    />
                  </div>
                </div>

                <div className="[display:flex]! [gap:12px] [margin-top:20px]!">
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
