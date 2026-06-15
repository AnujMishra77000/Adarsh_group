import { ArrowRight } from "lucide-react";
import { FormEvent, useMemo, useState } from "react";
import { useLocation, useNavigate } from "react-router-dom";
import { toast } from "sonner";

import { getAccessToken, getActiveAuthRole } from "@/features/auth/store";
import { getShopByPasscode, normalizePhone } from "@/features/shops/config";
import { setActiveShop } from "@/features/shops/store";
import { useActiveShop } from "@/features/shops/useActiveShop";

function getRedirectTarget(fromPath: string | undefined): string {
  if (!fromPath || fromPath === "/" || fromPath === "/login" || fromPath === "/shop-entry") {
    return "/landing";
  }
  return fromPath;
}

export function ShopEntryPage() {
  const navigate = useNavigate();
  const location = useLocation();
  const activeShop = useActiveShop();

  const [passcodeInput, setPasscodeInput] = useState("");

  const targetAfterSelection = useMemo(() => {
    const from = (location.state as { from?: string } | undefined)?.from;
    return getRedirectTarget(from);
  }, [location.state]);

  const onSubmit = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();

    const shop = getShopByPasscode(passcodeInput);
    if (!shop) {
      toast.error("Shop passcode not recognized. Please enter a valid registered shop mobile passcode.");
      return;
    }

    setActiveShop(shop.key);
    toast.success("Entering " + shop.name);
    const activeRole = getActiveAuthRole();
    const hasSession = Boolean(activeRole && getAccessToken(activeRole));
    if (hasSession) {
      navigate("/dashboard", { replace: true });
      return;
    }

    const target = targetAfterSelection === "/landing" ? `/shop/${shop.key}` : targetAfterSelection;
    navigate(target, { replace: true });
  };

  return (
    <div className="flex min-h-screen items-center justify-center bg-matte-gradient p-5 sm:p-8">
      <div className="w-full max-w-lg rounded-2xl border border-pink-300/25 bg-matte-900/80 p-6 shadow-neon-glow backdrop-blur sm:p-8">
        <h2 className="text-2xl font-semibold text-slate-100">Shop Entry</h2>
        <p className="mt-1 text-sm text-slate-300">Enter shop mobile passcode to continue.</p>

        <form className="mt-6 space-y-4" onSubmit={onSubmit}>
          <div>
            <label className="mb-1 block text-sm font-medium text-slate-200">Shop Mobile Passcode</label>
            <input
              value={passcodeInput}
              onChange={(event) => setPasscodeInput(normalizePhone(event.target.value))}
              maxLength={10}
              className="w-full rounded-lg border border-pink-300/30 bg-matte-800 px-3 py-2.5 text-sm text-slate-100 outline-none transition focus:border-pink-200"
              placeholder="Enter 10-digit shop passcode"
            />
          </div>

          <button
            type="submit"
            className="inline-flex items-center gap-2 rounded-lg border border-pink-300/45 bg-pink-400/15 px-4 py-2.5 text-sm font-semibold text-pink-50 shadow-neon-ring transition hover:bg-pink-400/25"
          >
            Continue to Shop CRM
            <ArrowRight size={15} />
          </button>
        </form>

        {activeShop && (
          <div className="mt-4 rounded-lg border border-pink-300/35 bg-pink-400/10 px-3 py-2 text-xs text-slate-200">
            <p>
              Active shop: <span className="font-semibold text-[#3f1a7a]">{activeShop.name}</span>
            </p>
            <button
              type="button"
              onClick={() => {
                const activeRole = getActiveAuthRole();
                const hasSession = Boolean(activeRole && getAccessToken(activeRole));
                navigate(hasSession ? "/dashboard" : `/shop/${activeShop.key}`, { replace: true });
              }}
              className="mt-2 rounded-md border border-pink-300/45 bg-pink-500/15 px-2.5 py-1 text-[11px] font-medium text-pink-50"
            >
              Continue with Active Shop
            </button>
          </div>
        )}
      </div>
    </div>
  );
}
