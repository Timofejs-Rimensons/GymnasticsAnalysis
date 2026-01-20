``import { useState } from "react";
import { Mail, Lock, User, Eye, EyeOff } from "lucide-react";
import { ApiService } from "../services/api";

interface AuthPageProps {
  onAuthSuccess: (token: string, username: string) => void;
  theme: "dark" | "light";
}

export default function AuthPage({ onAuthSuccess, theme }: AuthPageProps) {
  const [isLogin, setIsLogin] = useState(true);
  const [username, setUsername] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [showPassword, setShowPassword] = useState(false);
  const [showConfirmPassword, setShowConfirmPassword] = useState(false);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError("");
    setLoading(true);

    try {
      if (isLogin) {
        // Login
        const response = await ApiService.login(username, password);
        onAuthSuccess(response.access_token, response.user.username);
      } else {
        // Register
        if (password !== confirmPassword) {
          setError("Passwords do not match");
          setLoading(false);
          return;
        }
        if (password.length < 4) {
          setError("Password must be at least 4 characters");
          setLoading(false);
          return;
        }
        await ApiService.register(username, email, password);
        // Auto-login after registration
        const response = await ApiService.login(username, password);
        onAuthSuccess(response.access_token, response.user.username);
      }
    } catch (err: any) {
      setError(err.message || "Authentication failed");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div
      className={`min-h-screen flex items-center justify-center ${
        theme === "dark"
          ? "bg-gradient-to-br from-slate-900 via-purple-900 to-slate-900"
          : "bg-gradient-to-br from-blue-50 via-purple-50 to-blue-50"
      }`}
    >
      <div className="w-full max-w-md mx-auto px-4">
        {/* Header */}
        <div className="text-center mb-8">
          <h1
            className={`text-4xl font-bold mb-2 ${
              theme === "dark" ? "text-white" : "text-gray-900"
            }`}
          >
            Gymnastics Analysis
          </h1>
          <p
            className={`text-lg ${
              theme === "dark" ? "text-purple-200" : "text-purple-600"
            }`}
          >
            {isLogin ? "Welcome back" : "Create your account"}
          </p>
        </div>

        {/* Card */}
        <div
          className={`backdrop-blur-xl border rounded-2xl p-8 shadow-2xl ${
            theme === "dark"
              ? "bg-slate-800/50 border-purple-500/20"
              : "bg-white/60 border-purple-200"
          }`}
        >
          <form onSubmit={handleSubmit} className="space-y-6">
            {/* Username Field */}
            <div>
              <label
                className={`block text-sm font-medium mb-2 ${
                  theme === "dark" ? "text-white" : "text-gray-700"
                }`}
              >
                Username
              </label>
              <div
                className={`flex items-center border-2 rounded-lg px-4 py-3 transition ${
                  theme === "dark"
                    ? "bg-slate-700/50 border-purple-500/30 focus-within:border-purple-500"
                    : "bg-white/50 border-purple-200 focus-within:border-purple-500"
                }`}
              >
                <User className="w-5 h-5 text-purple-400 mr-3" />
                <input
                  type="text"
                  value={username}
                  onChange={(e) => setUsername(e.target.value)}
                  placeholder="Enter username"
                  className={`flex-1 bg-transparent outline-none ${
                    theme === "dark" ? "text-white placeholder:text-gray-400" : "text-gray-900 placeholder:text-gray-500"
                  }`}
                  required
                />
              </div>
            </div>

            {/* Email Field (Register Only) */}
            {!isLogin && (
              <div>
                <label
                  className={`block text-sm font-medium mb-2 ${
                    theme === "dark" ? "text-white" : "text-gray-700"
                  }`}
                >
                  Email
                </label>
                <div
                  className={`flex items-center border-2 rounded-lg px-4 py-3 transition ${
                    theme === "dark"
                      ? "bg-slate-700/50 border-purple-500/30 focus-within:border-purple-500"
                      : "bg-white/50 border-purple-200 focus-within:border-purple-500"
                  }`}
                >
                  <Mail className="w-5 h-5 text-purple-400 mr-3" />
                  <input
                    type="email"
                    value={email}
                    onChange={(e) => setEmail(e.target.value)}
                    placeholder="Enter email"
                    className={`flex-1 bg-transparent outline-none ${
                      theme === "dark" ? "text-white placeholder:text-gray-400" : "text-gray-900 placeholder:text-gray-500"
                    }`}
                    required
                  />
                </div>
              </div>
            )}

            {/* Password Field */}
            <div>
              <label
                className={`block text-sm font-medium mb-2 ${
                  theme === "dark" ? "text-white" : "text-gray-700"
                }`}
              >
                Password
              </label>
              <div
                className={`flex items-center border-2 rounded-lg px-4 py-3 transition ${
                  theme === "dark"
                    ? "bg-slate-700/50 border-purple-500/30 focus-within:border-purple-500"
                    : "bg-white/50 border-purple-200 focus-within:border-purple-500"
                }`}
              >
                <Lock className="w-5 h-5 text-purple-400 mr-3" />
                <input
                  type={showPassword ? "text" : "password"}
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  placeholder="Enter password"
                  className={`flex-1 bg-transparent outline-none ${
                    theme === "dark" ? "text-white placeholder:text-gray-400" : "text-gray-900 placeholder:text-gray-500"
                  }`}
                  required
                />
                <button
                  type="button"
                  onClick={() => setShowPassword(!showPassword)}
                  className="text-purple-400 hover:text-purple-300 ml-2"
                >
                  {showPassword ? <EyeOff className="w-5 h-5" /> : <Eye className="w-5 h-5" />}
                </button>
              </div>
            </div>

            {/* Confirm Password Field (Register Only) */}
            {!isLogin && (
              <div>
                <label
                  className={`block text-sm font-medium mb-2 ${
                    theme === "dark" ? "text-white" : "text-gray-700"
                  }`}
                >
                  Confirm Password
                </label>
                <div
                  className={`flex items-center border-2 rounded-lg px-4 py-3 transition ${
                    theme === "dark"
                      ? "bg-slate-700/50 border-purple-500/30 focus-within:border-purple-500"
                      : "bg-white/50 border-purple-200 focus-within:border-purple-500"
                  }`}
                >
                  <Lock className="w-5 h-5 text-purple-400 mr-3" />
                  <input
                    type={showConfirmPassword ? "text" : "password"}
                    value={confirmPassword}
                    onChange={(e) => setConfirmPassword(e.target.value)}
                    placeholder="Confirm password"
                    className={`flex-1 bg-transparent outline-none ${
                      theme === "dark" ? "text-white placeholder:text-gray-400" : "text-gray-900 placeholder:text-gray-500"
                    }`}
                    required
                  />
                  <button
                    type="button"
                    onClick={() => setShowConfirmPassword(!showConfirmPassword)}
                    className="text-purple-400 hover:text-purple-300 ml-2"
                  >
                    {showConfirmPassword ? <EyeOff className="w-5 h-5" /> : <Eye className="w-5 h-5" />}
                  </button>
                </div>
              </div>
            )}

            {/* Error Message */}
            {error && (
              <div className={`p-4 rounded-lg ${theme === "dark" ? "bg-red-500/20 border border-red-500/50" : "bg-red-100 border border-red-300"}`}>
                <p className={theme === "dark" ? "text-red-200" : "text-red-700"}>{error}</p>
              </div>
            )}

            {/* Submit Button */}
            <button
              type="submit"
              disabled={loading}
              className={`w-full py-3 rounded-lg font-semibold transition duration-300 ${
                loading
                  ? "opacity-50 cursor-not-allowed"
                  : "hover:scale-105 active:scale-95"
              } ${
                theme === "dark"
                  ? "bg-gradient-to-r from-purple-600 to-blue-600 text-white hover:from-purple-700 hover:to-blue-700"
                  : "bg-gradient-to-r from-purple-600 to-blue-600 text-white hover:from-purple-700 hover:to-blue-700"
              }`}
            >
              {loading ? "Processing..." : isLogin ? "Login" : "Register"}
            </button>

            {/* Toggle Auth Mode */}
            <p className={`text-center text-sm ${theme === "dark" ? "text-gray-400" : "text-gray-600"}`}>
              {isLogin ? "Don't have an account? " : "Already have an account? "}
              <button
                type="button"
                onClick={() => {
                  setIsLogin(!isLogin);
                  setError("");
                }}
                className={`font-semibold transition ${
                  theme === "dark"
                    ? "text-purple-400 hover:text-purple-300"
                    : "text-purple-600 hover:text-purple-700"
                }`}
              >
                {isLogin ? "Register" : "Login"}
              </button>
            </p>
          </form>
        </div>
      </div>
    </div>
  );
}
