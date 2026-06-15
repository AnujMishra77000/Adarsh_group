import { zodResolver } from "@hookform/resolvers/zod";
import { useMutation } from "@tanstack/react-query";
import { useForm } from "react-hook-form";
import { Link, useNavigate } from "react-router-dom";
import { toast } from "sonner";
import { z } from "zod";

import { registerAdmin } from "@/features/auth/api";
import { getErrorMessage } from "@/lib/errors";

const registerSchema = z.object({
  full_name: z.string().min(2, "Name is required"),
  email: z.string().email("Enter a valid email"),
  password: z.string().min(8, "Password must be at least 8 characters"),
  master_password: z.string().min(8, "Master password is required")
});

type RegisterFormValues = z.infer<typeof registerSchema>;

export function AdminRegisterPage() {
  const navigate = useNavigate();
  const {
    register,
    handleSubmit,
    formState: { errors }
  } = useForm<RegisterFormValues>({
    resolver: zodResolver(registerSchema),
    defaultValues: {
      full_name: "",
      email: "",
      password: "",
      master_password: ""
    }
  });

  const mutation = useMutation({
    mutationFn: registerAdmin,
    onSuccess: () => {
      toast.success("Admin registered successfully");
      navigate("/login/admin", { replace: true });
    },
    onError: (error) => {
      toast.error(getErrorMessage(error));
    }
  });

  return (
    <div>
      <h2 className="text-2xl font-semibold text-slate-100">Admin Registration</h2>
      <p className="mt-1 text-sm text-slate-300">Create a secure admin account using the master password.</p>

      <form className="mt-6 space-y-4" onSubmit={handleSubmit((values) => mutation.mutate(values))}>
        <div>
          <label className="mb-1 block text-sm font-medium text-slate-200">Full Name</label>
          <input
            type="text"
            {...register("full_name")}
            className="w-full rounded-lg border border-pink-300/30 bg-matte-800 px-3 py-2.5 text-sm text-slate-100 outline-none transition focus:border-pink-200"
            placeholder="Aadarsh Admin"
          />
          {errors.full_name && <p className="mt-1 text-xs text-rose-300">{errors.full_name.message}</p>}
        </div>

        <div>
          <label className="mb-1 block text-sm font-medium text-slate-200">Email</label>
          <input
            type="email"
            {...register("email")}
            className="w-full rounded-lg border border-pink-300/30 bg-matte-800 px-3 py-2.5 text-sm text-slate-100 outline-none transition focus:border-pink-200"
            placeholder="admin@shop.com"
          />
          {errors.email && <p className="mt-1 text-xs text-rose-300">{errors.email.message}</p>}
        </div>

        <div>
          <label className="mb-1 block text-sm font-medium text-slate-200">Password</label>
          <input
            type="password"
            {...register("password")}
            className="w-full rounded-lg border border-pink-300/30 bg-matte-800 px-3 py-2.5 text-sm text-slate-100 outline-none transition focus:border-pink-200"
            placeholder="Create secure password"
          />
          {errors.password && <p className="mt-1 text-xs text-rose-300">{errors.password.message}</p>}
        </div>

        <div>
          <label className="mb-1 block text-sm font-medium text-slate-200">Master Password</label>
          <input
            type="password"
            {...register("master_password")}
            className="w-full rounded-lg border border-pink-300/30 bg-matte-800 px-3 py-2.5 text-sm text-slate-100 outline-none transition focus:border-pink-200"
            placeholder="Enter master password"
          />
          {errors.master_password && <p className="mt-1 text-xs text-rose-300">{errors.master_password.message}</p>}
        </div>

        <button
          type="submit"
          disabled={mutation.isPending}
          className="w-full rounded-lg border border-pink-300/50 bg-pink-400/15 px-4 py-2.5 text-sm font-semibold text-pink-50 shadow-neon-ring transition hover:bg-pink-400/25 disabled:cursor-not-allowed disabled:opacity-60"
        >
          {mutation.isPending ? "Creating account..." : "Create Admin"}
        </button>
      </form>

      <div className="mt-5 space-y-2 text-sm text-slate-200">
        <p>
          Already registered?{" "}
          <Link className="text-pink-100 hover:text-pink-50" to="/login/admin">
            Login as Admin
          </Link>
        </p>
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
