import { zodResolver } from "@hookform/resolvers/zod";
import { useMutation } from "@tanstack/react-query";
import { useForm } from "react-hook-form";
import { Link, useLocation, useNavigate } from "react-router-dom";
import { toast } from "sonner";
import { z } from "zod";

import { fetchMe, login } from "@/features/auth/api";
import { clearAuthTokens, clearCurrentUser, getCurrentUser, setActiveAuthRole, setAuthTokens, setCurrentUser } from "@/features/auth/store";
import { getErrorMessage } from "@/lib/errors";
import type { UserProfile, UserRole } from "@/types/auth";

const loginSchema = z.object({
  email: z.string().email("Enter a valid email"),
  password: z.string().min(8, "Password must be at least 8 characters")
});

type LoginFormValues = z.infer<typeof loginSchema>;

type LoginPageProps = {
  mode: UserRole;
};

function getDisplayName(user: UserProfile | null): string {
  if (user === null) {
    return "";
  }

  const fullName = user.full_name?.trim();
  if (fullName) {
    return fullName;
  }

  if (user.email.includes("@")) {
    return user.email.split("@")[0];
  }

  return user.email;
}

export function LoginPage({ mode }: LoginPageProps) {
  const navigate = useNavigate();
  const location = useLocation();

  const {
    register,
    handleSubmit,
    formState: { errors }
  } = useForm<LoginFormValues>({
    resolver: zodResolver(loginSchema),
    defaultValues: {
      email: "",
      password: ""
    }
  });

  const modeLabel = mode === "admin" ? "Admin" : "Staff";
  const alternateMode = mode === "admin" ? "staff" : "admin";
  const existingProfileForMode = getCurrentUser(mode);
  const existingProfileName = getDisplayName(existingProfileForMode);

  const mutation = useMutation({
    mutationFn: login,
    onSuccess: async (tokens) => {
      setAuthTokens(tokens, mode);

      try {
        const profile = await fetchMe();
        if (profile.role !== mode) {
          clearAuthTokens(mode);
          clearCurrentUser(mode);
          toast.error("This account is configured as " + profile.role + ". Use the correct login card.");
          return;
        }

        setCurrentUser(profile, mode);

        const profileName = getDisplayName(profile);
        if (mode === "staff") {
          toast.success("Welcome " + profileName);
        } else {
          toast.success(modeLabel + " login successful");
        }

        const from = (location.state as { from?: string } | undefined)?.from;
        navigate(from && from !== "/" ? from : "/dashboard", { replace: true });
      } catch (error) {
        clearAuthTokens(mode);
        clearCurrentUser(mode);
        toast.error(getErrorMessage(error));
      }
    },
    onError: (error) => {
      clearAuthTokens(mode);
      clearCurrentUser(mode);
      toast.error(getErrorMessage(error));
    }
  });

  return (
    <div>
      <h2 className="text-2xl font-semibold text-slate-100">{modeLabel} Login</h2>
      <p className="mt-1 text-sm text-slate-300">Enter your credentials to continue.</p>

      {existingProfileName && (
        <div className="mt-3 rounded-lg border border-pink-300/35 bg-pink-400/10 px-3 py-2 text-xs text-pink-100">
          <p>Current {modeLabel} Session: {existingProfileName}</p>
          <button
            type="button"
            onClick={() => {
              setActiveAuthRole(mode);
              navigate("/dashboard", { replace: true });
            }}
            className="mt-2 rounded-md border border-pink-300/45 bg-pink-500/15 px-2.5 py-1 text-[11px] font-medium text-pink-50"
          >
            Continue as {modeLabel}
          </button>
        </div>
      )}

      <form className="mt-6 space-y-4" onSubmit={handleSubmit((values) => mutation.mutate(values))}>
        <div>
          <label className="mb-1 block text-sm font-medium text-slate-200">Email</label>
          <input
            type="email"
            {...register("email")}
            className="w-full rounded-lg border border-pink-300/30 bg-matte-800 px-3 py-2.5 text-sm text-slate-100 outline-none transition focus:border-pink-200"
            placeholder={mode === "admin" ? "admin@aadarsh-eye.com" : "staff@aadarsh-eye.com"}
          />
          {errors.email && <p className="mt-1 text-xs text-rose-300">{errors.email.message}</p>}
        </div>

        <div>
          <label className="mb-1 block text-sm font-medium text-slate-200">Password</label>
          <input
            type="password"
            {...register("password")}
            className="w-full rounded-lg border border-pink-300/30 bg-matte-800 px-3 py-2.5 text-sm text-slate-100 outline-none transition focus:border-pink-200"
            placeholder="Enter your password"
          />
          {errors.password && <p className="mt-1 text-xs text-rose-300">{errors.password.message}</p>}
        </div>

        <button
          type="submit"
          disabled={mutation.isPending}
          className="w-full rounded-lg border border-pink-300/50 bg-pink-400/15 px-4 py-2.5 text-sm font-semibold text-pink-50 shadow-neon-ring transition hover:bg-pink-400/25 disabled:cursor-not-allowed disabled:opacity-60"
        >
          {mutation.isPending ? "Signing in..." : "Sign In as " + modeLabel}
        </button>
      </form>

      <div className="mt-5 space-y-2 text-sm text-slate-200">
        <p>
          Need {alternateMode} access?{" "}
          <Link className="text-pink-100 hover:text-pink-50" to={"/login/" + alternateMode}>
            Login as {alternateMode === "admin" ? "Admin" : "Staff"}
          </Link>
        </p>

        {mode === "admin" && (
          <p>
            No admin account yet?{" "}
            <Link className="text-pink-100 hover:text-pink-50" to="/admin-register">
              Register Admin
            </Link>
          </p>
        )}

        <p>
          Back to access cards?{" "}
          <Link className="text-pink-100 hover:text-pink-50" to="/">
            Go to Landing
          </Link>
        </p>
      </div>
    </div>
  );
}
