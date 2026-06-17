import { ArrowRight } from "lucide-react";
import { FormEvent, useMemo, useState } from "react";
import { useMutation } from "@tanstack/react-query";
import { useLocation, useNavigate } from "react-router-dom";
import { toast } from "sonner";

import { getAccessToken, getActiveAuthRole } from "@/features/auth/store";
import { resolveShop } from "@/features/shops/api";
import { getActiveShops, getShopByKey } from "@/features/shops/config";
import { setActiveShop } from "@/features/shops/store";
import { useActiveShop } from "@/features/shops/useActiveShop";
import { getErrorMessage } from "@/lib/errors";
import { CRM_PATHS } from "@/lib/routes";

function getRedirectTarget(fromPath: string | undefined): string {
  if (
    !fromPath ||
    fromPath === "/" ||
    fromPath === CRM_PATHS.root ||
    fromPath === CRM_PATHS.login ||
    fromPath === CRM_PATHS.shopEntry ||
    fromPath === CRM_PATHS.landing
  ) {
    return CRM_PATHS.landing;
  }
  return fromPath;
}

function getPostSelectionTarget(targetAfterSelection: string, shopKey: string): string {
  if (targetAfterSelection === CRM_PATHS.landing) {
    return `${CRM_PATHS.shopResolver}/${shopKey}`;
  }
  if (targetAfterSelection.startsWith(CRM_PATHS.login) || targetAfterSelection === CRM_PATHS.adminRegister) {
    return targetAfterSelection;
  }
  return CRM_PATHS.landing;
}

export function ShopEntryPage() {
  const navigate = useNavigate();
  const location = useLocation();
  const activeShop = useActiveShop();
  const shopOptions = getActiveShops();
  const [identifierInput, setIdentifierInput] = useState("");

  const targetAfterSelection = useMemo(() => {
    const from = (location.state as { from?: string } | undefined)?.from;
    return getRedirectTarget(from);
  }, [location.state]);

  const completeShopSelection = (shopCode: string, displayName: string) => {
    const shop = getShopByKey(shopCode);
    if (!shop) {
      toast.error("Shop resolved but is not available in this app version. Please refresh and try again.");
      return;
    }

    setActiveShop(shop.key);
    toast.success("Entering " + displayName);
    const activeRole = getActiveAuthRole();
    const hasSession = Boolean(activeRole && getAccessToken(activeRole));
    if (hasSession) {
      navigate(CRM_PATHS.dashboard, { replace: true });
      return;
    }

    const target = getPostSelectionTarget(targetAfterSelection, shop.key);
    navigate(target, { replace: true });
  };

  const resolveMutation = useMutation({
    mutationFn: resolveShop,
    onSuccess: (shop) => {
      completeShopSelection(shop.code, shop.display_name);
    },
    onError: (error) => {
      toast.error(getErrorMessage(error));
    }
  });

  const onSubmit = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    const identifier = identifierInput.trim();
    if (!identifier) {
      toast.error("Enter a shop mobile number or center identifier.");
      return;
    }
    resolveMutation.mutate({ identifier });
  };

  return (
    <div className="flex min-h-screen items-center justify-center bg-matte-gradient p-5 sm:p-8">
      <div className="w-full max-w-lg rounded-2xl border border-pink-300/25 bg-matte-900/80 p-6 shadow-neon-glow backdrop-blur sm:p-8">
        <h2 className="text-2xl font-semibold text-slate-100">Shop Entry</h2>
        <p className="mt-1 text-sm text-slate-300">
          Enter your shop mobile number if it is configured on this environment, or choose your center below.
        </p>

        <form className="mt-6 space-y-4" onSubmit={onSubmit}>
          <div>
            <label htmlFor="shop-identifier" className="mb-1 block text-sm font-medium text-slate-200">
              Shop Identifier
            </label>
            <input
              id="shop-identifier"
              value={identifierInput}
              onChange={(event) => setIdentifierInput(event.target.value)}
              maxLength={80}
              className="w-full rounded-lg border border-pink-300/30 bg-matte-800 px-3 py-2.5 text-sm text-slate-100 outline-none transition focus:border-pink-200"
              placeholder="Enter shop mobile or center code"
            />
            <p className="mt-2 text-xs text-slate-400">
              Center codes like <span className="font-semibold text-slate-200">adarsh-eye-boutique</span> also work.
            </p>
          </div>

          <button
            type="submit"
            disabled={resolveMutation.isPending}
            className="inline-flex items-center gap-2 rounded-lg border border-pink-300/45 bg-pink-400/15 px-4 py-2.5 text-sm font-semibold text-pink-50 shadow-neon-ring transition hover:bg-pink-400/25 disabled:cursor-not-allowed disabled:opacity-60"
          >
            {resolveMutation.isPending ? "Checking..." : "Continue to Shop CRM"}
            <ArrowRight size={15} />
          </button>
        </form>

        <div className="mt-6 border-t border-pink-300/20 pt-5">
          <p className="text-sm font-medium text-slate-200">Choose your center directly</p>
          <div className="mt-3 grid gap-3 sm:grid-cols-2">
            {shopOptions.map((shop) => (
              <button
                key={shop.key}
                type="button"
                disabled={resolveMutation.isPending}
                onClick={() => {
                  resolveMutation.mutate({ identifier: shop.key });
                }}
                className="rounded-xl border border-pink-300/30 bg-pink-400/10 px-4 py-3 text-left transition hover:bg-pink-400/20 disabled:cursor-not-allowed disabled:opacity-60"
              >
                <span className="block text-sm font-semibold text-slate-100">Use {shop.name}</span>
                <span className="mt-1 block text-xs text-slate-300">
                  {shop.locationLabel || shop.centerType}
                </span>
              </button>
            ))}
          </div>
        </div>

        {activeShop && (
          <div className="mt-4 rounded-lg border border-pink-300/35 bg-pink-400/10 px-3 py-2 text-xs text-slate-200">
            <p>
              Active shop: <span className="font-semibold text-[#3f1a7a]">{activeShop.name}</span>
            </p>
            <button
              type="button"
              disabled={resolveMutation.isPending}
              onClick={() => {
                resolveMutation.mutate({ identifier: activeShop.key });
              }}
              className="mt-2 rounded-md border border-pink-300/45 bg-pink-500/15 px-2.5 py-1 text-[11px] font-medium text-pink-50 disabled:cursor-not-allowed disabled:opacity-60"
            >
              Continue with Active Shop
            </button>
          </div>
        )}
      </div>
    </div>
  );
}
