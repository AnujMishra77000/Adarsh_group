import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useEffect, useRef, useState } from "react";
import { useNavigate, useParams, useSearchParams } from "react-router-dom";
import { toast } from "sonner";

import { downloadBillPdf, generateBillPdf, getBill, getBillPdfPreviewUrl, sendBillEmail, sendBillWhatsapp } from "@/features/bills/api";
import { useCurrentUser } from "@/features/auth/useCurrentUser";
import { getErrorMessage } from "@/lib/errors";
import { CRM_PATHS } from "@/lib/routes";

function formatCurrency(value: number): string {
  return new Intl.NumberFormat("en-IN", {
    style: "currency",
    currency: "INR",
    maximumFractionDigits: 2,
    minimumFractionDigits: 2
  }).format(value);
}

function formatDate(value: string | null): string {
  if (value === null || value.length === 0) {
    return "-";
  }
  return new Date(value).toLocaleDateString();
}

export function BillingDetailPage() {
  const queryClient = useQueryClient();
  const navigate = useNavigate();
  const params = useParams<{ billId: string }>();
  const [searchParams] = useSearchParams();
  const currentUserQuery = useCurrentUser();

  const currentRole = currentUserQuery.data?.role;
  const canUpdateBills = currentRole === "admin" || currentRole === "staff";
  const focusPdf = searchParams.get("focus") === "pdf";
  const [pdfPreviewUrl, setPdfPreviewUrl] = useState<string | null>(null);
  const [pdfPreviewError, setPdfPreviewError] = useState<string | null>(null);
  const [isPdfPreviewLoading, setIsPdfPreviewLoading] = useState(false);

  const parsedBillId = Number(params.billId ?? 0);
  const billId = Number.isInteger(parsedBillId) && parsedBillId > 0 ? parsedBillId : null;

  const billQuery = useQuery({
    queryKey: ["bill", billId],
    queryFn: () => getBill(billId as number),
    enabled: billId !== null
  });

  useEffect(() => {
    let isActive = true;
    let objectUrl: string | null = null;

    setPdfPreviewUrl(null);
    setPdfPreviewError(null);

    if (billId === null || !billQuery.data?.pdf_url) {
      setIsPdfPreviewLoading(false);
      return () => undefined;
    }

    setIsPdfPreviewLoading(true);
    void getBillPdfPreviewUrl(billId)
      .then((url) => {
        objectUrl = url;
        if (isActive) {
          setPdfPreviewUrl(url);
        }
      })
      .catch((error) => {
        if (isActive) {
          setPdfPreviewError(getErrorMessage(error));
        }
      })
      .finally(() => {
        if (isActive) {
          setIsPdfPreviewLoading(false);
        }
      });

    return () => {
      isActive = false;
      if (objectUrl) {
        URL.revokeObjectURL(objectUrl);
      }
    };
  }, [billId, billQuery.data?.pdf_url]);

  const handleDownloadPdf = async () => {
    if (billId === null || !billQuery.data) {
      return;
    }

    try {
      await downloadBillPdf(billId, `${billQuery.data.bill_number}.pdf`);
    } catch (error) {
      toast.error(getErrorMessage(error));
    }
  };

  const generatePdfMutation = useMutation({
    mutationFn: generateBillPdf,
    onSuccess: (bill) => {
      toast.success("Bill PDF generated");
      queryClient.invalidateQueries({ queryKey: ["bills"] });
      queryClient.invalidateQueries({ queryKey: ["bill", bill.id] });
    },
    onError: (error) => toast.error(getErrorMessage(error))
  });

  const sendEmailMutation = useMutation({
    mutationFn: sendBillEmail,
    onSuccess: (response) => {
      toast.success(response.message || "Bill sent on email");
      if (billId !== null) {
        queryClient.invalidateQueries({ queryKey: ["bill", billId] });
      }
    },
    onError: (error) => toast.error(getErrorMessage(error))
  });

  const sendWhatsAppMutation = useMutation({
    mutationFn: sendBillWhatsapp,
    onSuccess: (response) => {
      toast.success(response.message || "Bill sent on WhatsApp");
      if (billId !== null) {
        queryClient.invalidateQueries({ queryKey: ["bill", billId] });
      }
    },
    onError: (error) => toast.error(getErrorMessage(error))
  });

  const hasAutoPdfTriggeredRef = useRef(false);

  useEffect(() => {
    if (!focusPdf || billId === null || hasAutoPdfTriggeredRef.current) {
      return;
    }
    if (!billQuery.data) {
      return;
    }
    if (billQuery.data.pdf_url) {
      return;
    }

    hasAutoPdfTriggeredRef.current = true;
    generatePdfMutation.mutate(billId);
  }, [billId, billQuery.data, focusPdf, generatePdfMutation]);

  if (billId === null) {
    return (
      <section className="rounded-2xl border border-rose-300/30 bg-rose-500/10 p-5 text-rose-100 shadow-neon-ring">
        <p className="text-sm">Invalid bill id.</p>
        <button
          type="button"
          onClick={() => navigate(CRM_PATHS.billingRecords)}
          className="mt-3 rounded-lg border border-pink-300/45 bg-pink-500/15 px-4 py-2 text-sm font-medium text-pink-100"
        >
          Back to Saved Bills
        </button>
      </section>
    );
  }

  return (
    <section className="space-y-6">
      <div className="rounded-2xl border border-pink-400/20 bg-matte-850/85 p-5 shadow-neon-ring">
        <div className="mb-4 flex flex-wrap items-end justify-between gap-3">
          <div>
            <h2 className="text-xl font-semibold text-slate-100">
              Bill Detail {billQuery.data ? `- ${billQuery.data.bill_number}` : ""}
            </h2>
            <p className="text-sm text-slate-400">
              Full-page view for bill details, updates, PDF preview, and send actions.
            </p>
          </div>

          <div className="flex flex-wrap gap-2">
            <button
              type="button"
              onClick={() => navigate(CRM_PATHS.billingRecords)}
              className="rounded-lg border border-slate-500/50 px-3 py-2 text-sm text-slate-200"
            >
              Back
            </button>
            {canUpdateBills && (
              <button
                type="button"
                onClick={() => navigate(`${CRM_PATHS.billing}/edit/${billId}`)}
                className="rounded-lg border border-amber-400/35 px-3 py-2 text-sm text-amber-200"
              >
                Update Bill
              </button>
            )}
            <button
              type="button"
              onClick={() => generatePdfMutation.mutate(billId)}
              disabled={generatePdfMutation.isPending}
              className="rounded-lg border border-pink-300/45 bg-pink-500/15 px-3 py-2 text-sm text-pink-100"
            >
              {generatePdfMutation.isPending ? "Generating..." : "Generate PDF"}
            </button>
            <button
              type="button"
              onClick={() => sendEmailMutation.mutate(billId)}
              disabled={sendEmailMutation.isPending}
              className="rounded-lg border border-sky-400/35 px-3 py-2 text-sm text-sky-200"
            >
              Send Email
            </button>
            <button
              type="button"
              onClick={() => sendWhatsAppMutation.mutate(billId)}
              disabled={sendWhatsAppMutation.isPending}
              className="rounded-lg border border-emerald-400/35 px-3 py-2 text-sm text-emerald-200"
            >
              Send WhatsApp
            </button>
          </div>
        </div>

        {billQuery.isLoading && <p className="text-sm text-slate-300">Loading bill...</p>}
        {billQuery.isError && <p className="text-sm text-rose-400">{getErrorMessage(billQuery.error)}</p>}

        {billQuery.data && (
          <div className="space-y-5">
            <div className="grid gap-4 text-sm text-slate-300 sm:grid-cols-2 lg:grid-cols-3">
              <p className="font-medium text-pink-200">{billQuery.data.bill_number}</p>
              <p>{billQuery.data.customer_name_snapshot}</p>
              <p>Customer ID: {billQuery.data.customer_business_id || "-"}</p>
              <p>Mobile: {billQuery.data.customer_contact_no || "-"}</p>
              <p>Grand Total: {formatCurrency(Number(billQuery.data.grand_total))}</p>
              <p>Paid: {formatCurrency(Number(billQuery.data.paid_total))}</p>
              <p>Balance: {formatCurrency(Number(billQuery.data.balance_amount))}</p>
              <p>Payment Status: {billQuery.data.payment_status.toUpperCase()}</p>
              <p>Delivery: {formatDate(billQuery.data.delivery_date)}</p>
              <p>Created: {new Date(billQuery.data.created_at).toLocaleString()}</p>
              <p>Updated: {new Date(billQuery.data.updated_at).toLocaleString()}</p>
              <p className="sm:col-span-2 lg:col-span-3">Notes: {billQuery.data.notes || "-"}</p>
            </div>

            <div className="overflow-x-auto">
              <table className="min-w-full text-left text-sm text-slate-300">
                <thead className="text-xs uppercase text-slate-400">
                  <tr>
                    <th className="py-2 pr-3">Type</th>
                    <th className="py-2 pr-3">Item</th>
                    <th className="py-2 pr-3 text-right">Qty</th>
                    <th className="py-2 pr-3 text-right">Unit</th>
                    <th className="py-2 pr-3 text-right">Discount</th>
                    <th className="py-2 text-right">Line Total</th>
                  </tr>
                </thead>
                <tbody>
                  {billQuery.data.items.map((item) => (
                    <tr key={item.id} className="border-t border-slate-800/80">
                      <td className="py-2 pr-3">{item.item_type.replace("_", " ").toUpperCase()}</td>
                      <td className="py-2 pr-3">{item.item_name}</td>
                      <td className="py-2 pr-3 text-right">{Number(item.quantity).toFixed(2)}</td>
                      <td className="py-2 pr-3 text-right">{formatCurrency(Number(item.unit_price))}</td>
                      <td className="py-2 pr-3 text-right">{formatCurrency(Number(item.discount))}</td>
                      <td className="py-2 text-right">{formatCurrency(Number(item.line_total))}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>

            <div className="grid gap-3 text-sm text-slate-300 sm:grid-cols-2 lg:grid-cols-4">
              <p>Subtotal: {formatCurrency(Number(billQuery.data.subtotal))}</p>
              <p>Discount: {formatCurrency(Number(billQuery.data.discount_total))}</p>
              <p>Tax: {formatCurrency(Number(billQuery.data.tax_total))}</p>
              <p>Grand: {formatCurrency(Number(billQuery.data.grand_total))}</p>
            </div>

            <div className="overflow-x-auto">
              <table className="min-w-full text-left text-sm text-slate-300">
                <thead className="text-xs uppercase text-slate-400">
                  <tr>
                    <th className="py-2 pr-3">Mode</th>
                    <th className="py-2 pr-3 text-right">Amount</th>
                    <th className="py-2 pr-3">Paid At</th>
                    <th className="py-2">Reference</th>
                  </tr>
                </thead>
                <tbody>
                  {billQuery.data.payments.length === 0 && (
                    <tr className="border-t border-slate-800/80">
                      <td className="py-2 text-slate-400" colSpan={4}>
                        No payments recorded.
                      </td>
                    </tr>
                  )}
                  {billQuery.data.payments.map((payment) => (
                    <tr key={payment.id} className="border-t border-slate-800/80">
                      <td className="py-2 pr-3">{payment.mode.replace("_", " ").toUpperCase()}</td>
                      <td className="py-2 pr-3 text-right">{formatCurrency(Number(payment.amount))}</td>
                      <td className="py-2 pr-3">{new Date(payment.paid_at).toLocaleString()}</td>
                      <td className="py-2">{payment.reference_no || "-"}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        )}
      </div>

      <div className="rounded-2xl border border-pink-400/20 bg-matte-850/85 p-5 shadow-neon-ring">
        <div className="mb-3 flex items-center justify-between gap-3">
          <h3 className="text-lg font-semibold text-slate-100">Bill PDF Preview</h3>
          {billQuery.data?.pdf_url && (
            <button
              type="button"
              onClick={() => void handleDownloadPdf()}
              className="rounded-md border border-emerald-400/35 px-3 py-1.5 text-xs text-emerald-200"
            >
              Download PDF
            </button>
          )}
        </div>

        {!billQuery.data?.pdf_url && (
          <div className="rounded-lg border border-dashed border-slate-700 p-6 text-center text-sm text-slate-400">
            No PDF generated yet. Click Generate PDF to create and preview it.
          </div>
        )}

        {billQuery.data?.pdf_url && isPdfPreviewLoading && (
          <div className="rounded-lg border border-dashed border-slate-700 p-6 text-center text-sm text-slate-400">
            Loading secured PDF preview...
          </div>
        )}

        {billQuery.data?.pdf_url && pdfPreviewError && (
          <div className="rounded-lg border border-rose-300/30 bg-rose-500/10 p-4 text-sm text-rose-100">
            {pdfPreviewError}
          </div>
        )}

        {billQuery.data?.pdf_url && pdfPreviewUrl && (
          <iframe
            title={`Bill PDF ${billQuery.data.bill_number}`}
            src={pdfPreviewUrl}
            className="h-[75vh] w-full rounded-lg border border-pink-400/20 bg-white"
          />
        )}
      </div>
    </section>
  );
}
