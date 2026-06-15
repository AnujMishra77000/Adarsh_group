import { useEffect } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";

import { getShopByKey, getShopByPhone } from "@/features/shops/config";
import { setActiveShop } from "@/features/shops/store";

export function ShopResolvePage() {
  const navigate = useNavigate();
  const params = useParams<{ shopKey: string }>();

  const incomingShopKey = params.shopKey ?? null;
  const shop = getShopByKey(incomingShopKey) ?? getShopByPhone(incomingShopKey ?? "");

  useEffect(() => {
    if (!shop) {
      return;
    }

    setActiveShop(shop.key);
    navigate("/landing", { replace: true });
  }, [navigate, shop]);

  if (shop) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-matte-gradient p-5 text-slate-100">
        <div className="rounded-2xl border border-pink-300/30 bg-matte-900/80 p-6 text-sm shadow-neon-glow">
          Redirecting to {shop.name}...
        </div>
      </div>
    );
  }

  return (
    <div className="flex min-h-screen items-center justify-center bg-matte-gradient p-5">
      <div className="w-full max-w-xl rounded-2xl border border-rose-300/30 bg-matte-900/85 p-6 text-slate-100 shadow-neon-glow">
        <h2 className="text-lg font-semibold text-rose-200">Invalid Shop Entry Link</h2>
        <p className="mt-2 text-sm text-slate-300">Please enter a valid shop mobile passcode to continue.</p>
        <Link to="/" className="mt-5 inline-block text-sm text-pink-100 hover:text-pink-50">
          Go to Shop Number Entry
        </Link>
      </div>
    </div>
  );
}
