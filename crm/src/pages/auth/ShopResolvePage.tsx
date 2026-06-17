import { useEffect } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";
import { useMutation } from "@tanstack/react-query";

import { resolveShop } from "@/features/shops/api";
import { getShopByKey } from "@/features/shops/config";
import { setActiveShop } from "@/features/shops/store";
import { getErrorMessage } from "@/lib/errors";
import { CRM_PATHS } from "@/lib/routes";

export function ShopResolvePage() {
  const navigate = useNavigate();
  const params = useParams<{ shopKey: string }>();

  const incomingShopKey = params.shopKey ?? null;
  const {
    mutate: resolveShopIdentifier,
    isPending,
    isSuccess,
    isError,
    error
  } = useMutation({
    mutationFn: resolveShop,
    onSuccess: (resolvedShop) => {
      const shop = getShopByKey(resolvedShop.code);
      if (!shop) {
        return;
      }

      setActiveShop(shop.key);
      navigate(CRM_PATHS.landing, { replace: true });
    }
  });

  useEffect(() => {
    if (!incomingShopKey) {
      return;
    }

    resolveShopIdentifier({ identifier: incomingShopKey });
  }, [incomingShopKey, resolveShopIdentifier]);

  if (isPending || isSuccess) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-matte-gradient p-5 text-slate-100">
        <div className="rounded-2xl border border-pink-300/30 bg-matte-900/80 p-6 text-sm shadow-neon-glow">
          Resolving shop entry...
        </div>
      </div>
    );
  }

  return (
    <div className="flex min-h-screen items-center justify-center bg-matte-gradient p-5">
      <div className="w-full max-w-xl rounded-2xl border border-rose-300/30 bg-matte-900/85 p-6 text-slate-100 shadow-neon-glow">
        <h2 className="text-lg font-semibold text-rose-200">Invalid Shop Entry Link</h2>
        <p className="mt-2 text-sm text-slate-300">Please select a valid Adarsh Optical Group center to continue.</p>
        {isError && (
          <p className="mt-2 text-xs text-rose-300">{getErrorMessage(error)}</p>
        )}
        <Link to={CRM_PATHS.shopEntry} className="mt-5 inline-block text-sm text-pink-100 hover:text-pink-50">
          Go to Center Selection
        </Link>
      </div>
    </div>
  );
}
