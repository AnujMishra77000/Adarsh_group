import { zodResolver } from "@hookform/resolvers/zod";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { CalendarPlus, ChevronRight, History, Search, UserPlus } from "lucide-react";
import { useState } from "react";
import { useForm } from "react-hook-form";
import { useNavigate } from "react-router-dom";
import { toast } from "sonner";
import { z } from "zod";

import { createCustomer, listCustomers, searchCustomers } from "@/features/customers/api";
import { useActiveShop } from "@/features/shops/useActiveShop";
import { createVisit } from "@/features/visits/api";
import { getErrorMessage } from "@/lib/errors";
import { CRM_PATHS } from "@/lib/routes";
import type { Customer, CustomerPayload } from "@/types/customer";
import type { VisitPayload } from "@/types/visit";

const optionalEmail = z
  .string()
  .trim()
  .optional()
  .transform((value) => value || null)
  .refine((value) => (value ? /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(value) : true), {
    message: "Enter a valid email"
  });

const optionalText = z
  .string()
  .trim()
  .optional()
  .transform((value) => value || null);

const optionalPhone = z
  .string()
  .trim()
  .optional()
  .transform((value) => value || null)
  .refine((value) => value === null || value.length >= 8, {
    message: "Enter at least 8 digits"
  });

const ageField = z.preprocess(
  (value) => {
    if (value === "" || value === null || value === undefined) {
      return null;
    }
    const numeric = Number(value);
    return Number.isNaN(numeric) ? value : numeric;
  },
  z.number({ invalid_type_error: "Enter a valid age" }).int().min(0).max(130).nullable()
);

const patientVisitFormSchema = z.object({
  name: z.string().trim().min(2, "Patient name is required"),
  age: ageField,
  contact_no: z.string().trim().min(8, "Contact number is required"),
  email: optionalEmail,
  whatsapp_no: optionalPhone,
  gender: z.preprocess(
    (value) => (value === "" || value === undefined ? null : value),
    z.enum(["male", "female", "other"]).nullable()
  ),
  occupation: optionalText,
  guardian_name: optionalText,
  guardian_contact_no: optionalPhone,
  address: optionalText,
  whatsapp_opt_in: z.boolean(),
  visit_date: z.string().min(1, "Visit date is required"),
  reason_for_visit: z.string().trim().min(2, "Reason for visit is required"),
  referred_by: optionalText,
  visit_notes: optionalText,
  visit_status: z.enum(["draft", "in_progress"])
});

const visitFormSchema = z.object({
  visit_date: z.string().min(1, "Visit date is required"),
  reason_for_visit: z.string().trim().min(2, "Reason for visit is required"),
  referred_by: optionalText,
  visit_notes: optionalText,
  visit_status: z.enum(["draft", "in_progress"])
});

type PatientVisitFormValues = z.infer<typeof patientVisitFormSchema>;
type VisitFormValues = z.infer<typeof visitFormSchema>;
type WorkflowMode = "search" | "new-patient" | "start-visit";

function makeIdempotencyKey(prefix: string): string {
  if (typeof crypto !== "undefined" && "randomUUID" in crypto) {
    return `${prefix}-${crypto.randomUUID()}`;
  }
  return `${prefix}-${Date.now()}-${Math.random().toString(36).slice(2)}`;
}

function currentDateTimeLocal(): string {
  const now = new Date();
  now.setMinutes(now.getMinutes() - now.getTimezoneOffset());
  return now.toISOString().slice(0, 16);
}

function createPatientDefaults(): PatientVisitFormValues {
  return {
    name: "",
    age: null,
    contact_no: "",
    email: "",
    whatsapp_no: "",
    gender: null,
    occupation: "",
    guardian_name: "",
    guardian_contact_no: "",
    address: "",
    whatsapp_opt_in: false,
    visit_date: currentDateTimeLocal(),
    reason_for_visit: "",
    referred_by: "",
    visit_notes: "",
    visit_status: "draft"
  };
}

function createVisitDefaults(): VisitFormValues {
  return {
    visit_date: currentDateTimeLocal(),
    reason_for_visit: "",
    referred_by: "",
    visit_notes: "",
    visit_status: "draft"
  };
}

export function CustomersPage() {
  const queryClient = useQueryClient();
  const navigate = useNavigate();
  const activeShop = useActiveShop();
  const [mode, setMode] = useState<WorkflowMode>("search");
  const [searchInput, setSearchInput] = useState("");
  const [selectedPatient, setSelectedPatient] = useState<Customer | null>(null);
  const [patientRegistrationKey, setPatientRegistrationKey] = useState(() => makeIdempotencyKey("patient"));
  const [visitIdempotencyKey, setVisitIdempotencyKey] = useState(() => makeIdempotencyKey("visit"));
  const [recoveryMessage, setRecoveryMessage] = useState<string | null>(null);

  const patientForm = useForm<PatientVisitFormValues>({
    resolver: zodResolver(patientVisitFormSchema),
    defaultValues: createPatientDefaults()
  });

  const visitForm = useForm<VisitFormValues>({
    resolver: zodResolver(visitFormSchema),
    defaultValues: createVisitDefaults()
  });

  const searchMutation = useMutation({
    mutationFn: async (query: string) => {
      const trimmed = query.trim();
      if (trimmed.length === 0) {
        return listCustomers({ page: 1, page_size: 10 });
      }
      return searchCustomers(trimmed, 1, 20);
    }
  });

  const createPatientMutation = useMutation({
    mutationFn: createCustomer
  });

  const createVisitMutation = useMutation({
    mutationFn: createVisit
  });

  const searchResults = searchMutation.data?.items ?? [];
  const isSaving = createPatientMutation.isPending || createVisitMutation.isPending;

  const invalidatePatientQueries = () => {
    queryClient.invalidateQueries({ queryKey: ["customers"] });
    queryClient.invalidateQueries({ queryKey: ["customer-records"] });
    queryClient.invalidateQueries({ queryKey: ["customer-record-detail"] });
    queryClient.invalidateQueries({ queryKey: ["visits"] });
  };

  const openNewPatient = () => {
    setMode("new-patient");
    setRecoveryMessage(null);
    setSelectedPatient(null);
    setPatientRegistrationKey(makeIdempotencyKey("patient"));
    setVisitIdempotencyKey(makeIdempotencyKey("visit"));
    patientForm.reset(createPatientDefaults());
  };

  const openVisitForPatient = (patient: Customer) => {
    setSelectedPatient(patient);
    setMode("start-visit");
    setRecoveryMessage(null);
    setVisitIdempotencyKey(makeIdempotencyKey("visit"));
    visitForm.reset(createVisitDefaults());
  };

  const onSearchSubmit = (event: React.FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    searchMutation.mutate(searchInput, {
      onError: (error) => toast.error(getErrorMessage(error))
    });
  };

  const buildVisitPayload = (patientId: number, values: VisitFormValues | PatientVisitFormValues): VisitPayload => ({
    customer_id: patientId,
    visit_date: values.visit_date,
    reason_for_visit: values.reason_for_visit,
    referred_by: values.referred_by,
    visit_notes: values.visit_notes,
    status: values.visit_status,
    idempotency_key: visitIdempotencyKey
  });

  const navigateToVisit = (visitId: number) => {
    invalidatePatientQueries();
    navigate(`${CRM_PATHS.visitWorkspace}/${visitId}`);
  };

  const onRegisterPatientAndStartVisit = async (values: PatientVisitFormValues) => {
    const patientPayload: CustomerPayload = {
      name: values.name,
      age: values.age,
      contact_no: values.contact_no,
      email: values.email,
      whatsapp_no: values.whatsapp_no,
      gender: values.gender,
      occupation: values.occupation,
      guardian_name: values.guardian_name,
      guardian_contact_no: values.guardian_contact_no,
      address: values.address,
      purpose_of_visit: null,
      whatsapp_opt_in: values.whatsapp_opt_in,
      registration_idempotency_key: patientRegistrationKey
    };

    try {
      const patient = await createPatientMutation.mutateAsync(patientPayload);
      setSelectedPatient(patient);

      try {
        const visit = await createVisitMutation.mutateAsync(buildVisitPayload(patient.id, values));
        toast.success("Patient registered and visit started");
        setPatientRegistrationKey(makeIdempotencyKey("patient"));
        setVisitIdempotencyKey(makeIdempotencyKey("visit"));
        patientForm.reset(createPatientDefaults());
        navigateToVisit(visit.id);
      } catch (visitError) {
        setMode("start-visit");
        visitForm.reset({
          visit_date: values.visit_date,
          reason_for_visit: values.reason_for_visit,
          referred_by: values.referred_by,
          visit_notes: values.visit_notes,
          visit_status: values.visit_status
        });
        setRecoveryMessage(
          `Patient ${patient.name} was registered, but the visit was not started. Review the visit details and try again. ${getErrorMessage(
            visitError
          )}`
        );
        toast.error("Patient saved, visit start failed");
      }
    } catch (error) {
      toast.error(getErrorMessage(error));
    }
  };

  const onStartVisit = async (values: VisitFormValues) => {
    if (!selectedPatient) {
      toast.error("Select a patient before starting a visit");
      return;
    }

    try {
      const visit = await createVisitMutation.mutateAsync(buildVisitPayload(selectedPatient.id, values));
      toast.success("Visit started");
      setVisitIdempotencyKey(makeIdempotencyKey("visit"));
      visitForm.reset(createVisitDefaults());
      navigateToVisit(visit.id);
    } catch (error) {
      toast.error(getErrorMessage(error));
    }
  };

  return (
    <div className="space-y-6">
      <section className="rounded-2xl border border-pink-300/20 bg-matte-850/90 p-5 shadow-neon-ring">
        <div className="mb-5 flex flex-col gap-4 lg:flex-row lg:items-end lg:justify-between">
          <div>
            <p className="text-xs font-semibold uppercase tracking-[0.24em] text-pink-200/80">
              {activeShop?.name ?? "Adarsh Optical Group"}
            </p>
            <h2 className="mt-1 text-2xl font-semibold text-slate-100">Search Patient</h2>
            <p className="mt-1 text-sm text-slate-300">
              Find an existing patient, register a new patient, or begin today&apos;s visit.
            </p>
          </div>

          <div className="flex flex-wrap gap-2">
            <button
              type="button"
              onClick={openNewPatient}
              className="inline-flex items-center gap-2 rounded-lg border border-pink-300/45 bg-pink-500/15 px-3 py-2 text-sm font-medium text-pink-50 hover:bg-neon-pink/20"
            >
              <UserPlus size={16} />
              New Patient
            </button>
            <button
              type="button"
              disabled={!selectedPatient}
              onClick={() => selectedPatient && openVisitForPatient(selectedPatient)}
              className="inline-flex items-center gap-2 rounded-lg border border-emerald-300/35 bg-emerald-400/10 px-3 py-2 text-sm font-medium text-emerald-100 disabled:cursor-not-allowed disabled:opacity-45"
            >
              <CalendarPlus size={16} />
              Start New Visit
            </button>
            <button
              type="button"
              onClick={() => navigate(CRM_PATHS.customerRecords)}
              className="inline-flex items-center gap-2 rounded-lg border border-slate-500/45 bg-slate-700/20 px-3 py-2 text-sm font-medium text-slate-100 hover:border-pink-300/35"
            >
              <History size={16} />
              View History
            </button>
          </div>
        </div>

        <form onSubmit={onSearchSubmit} className="flex flex-col gap-2 md:flex-row">
          <div className="relative flex-1">
            <Search className="pointer-events-none absolute left-3 top-1/2 -translate-y-1/2 text-slate-400" size={16} />
            <input
              value={searchInput}
              onChange={(event) => setSearchInput(event.target.value)}
              placeholder="Name, patient ID, contact number, email, or WhatsApp"
              className="h-11 w-full rounded-lg border border-pink-300/35 bg-matte-800 pl-9 pr-3 text-sm text-slate-100 outline-none transition-all duration-300 focus:border-neon-pink/70 focus:ring-2 focus:ring-neon-pink/20"
            />
          </div>
          <button
            type="submit"
            disabled={searchMutation.isPending}
            className="h-11 rounded-lg border border-pink-300/45 bg-pink-500/15 px-4 text-sm font-medium text-pink-100 hover:bg-neon-pink/25 disabled:opacity-60"
          >
            Search
          </button>
        </form>
      </section>

      {recoveryMessage && (
        <section className="rounded-2xl border border-amber-300/30 bg-amber-400/10 p-4 text-sm text-amber-50">
          {recoveryMessage}
        </section>
      )}

      <div className="grid gap-6 xl:grid-cols-[1fr_1.05fr]">
        <section className="rounded-2xl border border-pink-300/20 bg-matte-850/90 p-5 shadow-neon-ring">
          <div className="mb-4 flex items-center justify-between gap-3">
            <div>
              <h3 className="text-lg font-semibold text-slate-100">Patient Results</h3>
              <p className="text-sm text-slate-300">Selected patient becomes the visit context.</p>
            </div>
            {searchMutation.data && <span className="text-xs text-slate-400">{searchMutation.data.total} found</span>}
          </div>

          {searchMutation.isIdle && (
            <p className="rounded-lg border border-dashed border-slate-600 p-5 text-sm text-slate-300">
              Search by phone number or patient ID to continue an existing record.
            </p>
          )}
          {searchMutation.isPending && <p className="text-sm text-slate-200">Searching patients...</p>}
          {searchMutation.isError && <p className="text-sm text-rose-200">{getErrorMessage(searchMutation.error)}</p>}
          {searchMutation.isSuccess && searchResults.length === 0 && (
            <div className="rounded-lg border border-dashed border-slate-600 p-5 text-sm text-slate-300">
              <p>No matching patient found.</p>
              <button
                type="button"
                onClick={openNewPatient}
                className="mt-3 inline-flex items-center gap-2 rounded-lg border border-pink-300/40 bg-pink-500/15 px-3 py-2 text-sm font-medium text-pink-50"
              >
                <UserPlus size={16} />
                Register New Patient
              </button>
            </div>
          )}

          {searchResults.length > 0 && (
            <div className="space-y-3">
              {searchResults.map((patient) => {
                const selected = selectedPatient?.id === patient.id;
                return (
                  <article
                    key={patient.id}
                    className={`rounded-xl border p-4 transition ${
                      selected ? "border-pink-300/45 bg-pink-400/10" : "border-slate-700/70 bg-matte-800/65"
                    }`}
                  >
                    <div className="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
                      <div>
                        <p className="font-semibold text-slate-100">{patient.name}</p>
                        <p className="mt-1 text-xs uppercase tracking-wide text-pink-100">{patient.customer_id}</p>
                        <p className="mt-2 text-sm text-slate-300">
                          {patient.contact_no}
                          {patient.whatsapp_no ? ` / WhatsApp ${patient.whatsapp_no}` : ""}
                        </p>
                        <p className="text-sm text-slate-400">
                          {[patient.gender, patient.age !== null ? `${patient.age} yrs` : null, patient.occupation]
                            .filter(Boolean)
                            .join(" · ") || "Basic details available"}
                        </p>
                      </div>

                      <div className="flex flex-wrap gap-2">
                        <button
                          type="button"
                          onClick={() => {
                            setSelectedPatient(patient);
                            setMode("search");
                          }}
                          className="rounded-lg border border-pink-300/35 px-3 py-2 text-xs font-medium text-pink-100 hover:border-pink-200"
                        >
                          Select
                        </button>
                        <button
                          type="button"
                          onClick={() => openVisitForPatient(patient)}
                          className="rounded-lg border border-emerald-300/35 px-3 py-2 text-xs font-medium text-emerald-100 hover:border-emerald-200"
                        >
                          Start Visit
                        </button>
                        <button
                          type="button"
                          onClick={() => navigate(`${CRM_PATHS.customerRecords}?q=${encodeURIComponent(patient.customer_id)}`)}
                          className="rounded-lg border border-slate-500/45 px-3 py-2 text-xs font-medium text-slate-200 hover:border-pink-300/35"
                        >
                          History
                        </button>
                      </div>
                    </div>
                  </article>
                );
              })}
            </div>
          )}
        </section>

        <section className="rounded-2xl border border-pink-300/20 bg-matte-850/90 p-5 shadow-neon-ring">
          {mode === "new-patient" && (
            <form className="space-y-5" onSubmit={patientForm.handleSubmit(onRegisterPatientAndStartVisit)}>
              <div>
                <h3 className="text-lg font-semibold text-slate-100">New Patient</h3>
                <p className="text-sm text-slate-300">
                  Patient details are saved once; today&apos;s visit is created as a separate record.
                </p>
              </div>

              <div className="grid gap-3 md:grid-cols-12">
                <div className="md:col-span-5">
                  <label className="mb-1 block text-xs font-medium uppercase tracking-wide text-slate-300">Patient Name</label>
                  <input
                    {...patientForm.register("name")}
                    className="h-11 w-full rounded-lg border border-pink-300/35 bg-matte-800 px-3 text-sm text-slate-100 outline-none focus:border-neon-pink/70"
                  />
                  {patientForm.formState.errors.name && (
                    <p className="mt-1 text-xs text-rose-300">{patientForm.formState.errors.name.message}</p>
                  )}
                </div>
                <div className="md:col-span-2">
                  <label className="mb-1 block text-xs font-medium uppercase tracking-wide text-slate-300">Age</label>
                  <input
                    type="number"
                    min="0"
                    {...patientForm.register("age")}
                    className="h-11 w-full rounded-lg border border-pink-300/35 bg-matte-800 px-3 text-sm text-slate-100 outline-none focus:border-neon-pink/70"
                  />
                </div>
                <div className="md:col-span-2">
                  <label className="mb-1 block text-xs font-medium uppercase tracking-wide text-slate-300">Gender</label>
                  <select
                    {...patientForm.register("gender")}
                    className="h-11 w-full rounded-lg border border-pink-300/35 bg-matte-800 px-3 text-sm text-slate-100 outline-none focus:border-neon-pink/70"
                  >
                    <option value="">Select</option>
                    <option value="male">Male</option>
                    <option value="female">Female</option>
                    <option value="other">Other</option>
                  </select>
                </div>
                <div className="md:col-span-3">
                  <label className="mb-1 block text-xs font-medium uppercase tracking-wide text-slate-300">Contact Number</label>
                  <input
                    {...patientForm.register("contact_no")}
                    className="h-11 w-full rounded-lg border border-pink-300/35 bg-matte-800 px-3 text-sm text-slate-100 outline-none focus:border-neon-pink/70"
                  />
                  {patientForm.formState.errors.contact_no && (
                    <p className="mt-1 text-xs text-rose-300">{patientForm.formState.errors.contact_no.message}</p>
                  )}
                </div>
              </div>

              <div className="grid gap-3 md:grid-cols-2">
                <div>
                  <label className="mb-1 block text-xs font-medium uppercase tracking-wide text-slate-300">Email</label>
                  <input
                    type="email"
                    {...patientForm.register("email")}
                    className="h-11 w-full rounded-lg border border-pink-300/35 bg-matte-800 px-3 text-sm text-slate-100 outline-none focus:border-neon-pink/70"
                  />
                  {patientForm.formState.errors.email && (
                    <p className="mt-1 text-xs text-rose-300">{patientForm.formState.errors.email.message}</p>
                  )}
                </div>
                <div>
                  <label className="mb-1 block text-xs font-medium uppercase tracking-wide text-slate-300">WhatsApp Number</label>
                  <input
                    {...patientForm.register("whatsapp_no")}
                    className="h-11 w-full rounded-lg border border-pink-300/35 bg-matte-800 px-3 text-sm text-slate-100 outline-none focus:border-neon-pink/70"
                  />
                </div>
              </div>

              <div className="grid gap-3 md:grid-cols-3">
                <div>
                  <label className="mb-1 block text-xs font-medium uppercase tracking-wide text-slate-300">Occupation</label>
                  <input
                    {...patientForm.register("occupation")}
                    className="h-11 w-full rounded-lg border border-pink-300/35 bg-matte-800 px-3 text-sm text-slate-100 outline-none focus:border-neon-pink/70"
                  />
                </div>
                <div>
                  <label className="mb-1 block text-xs font-medium uppercase tracking-wide text-slate-300">Guardian Name</label>
                  <input
                    {...patientForm.register("guardian_name")}
                    className="h-11 w-full rounded-lg border border-pink-300/35 bg-matte-800 px-3 text-sm text-slate-100 outline-none focus:border-neon-pink/70"
                  />
                </div>
                <div>
                  <label className="mb-1 block text-xs font-medium uppercase tracking-wide text-slate-300">Guardian Contact</label>
                  <input
                    {...patientForm.register("guardian_contact_no")}
                    className="h-11 w-full rounded-lg border border-pink-300/35 bg-matte-800 px-3 text-sm text-slate-100 outline-none focus:border-neon-pink/70"
                  />
                  {patientForm.formState.errors.guardian_contact_no && (
                    <p className="mt-1 text-xs text-rose-300">{patientForm.formState.errors.guardian_contact_no.message}</p>
                  )}
                </div>
              </div>

              <div>
                <label className="mb-1 block text-xs font-medium uppercase tracking-wide text-slate-300">Address</label>
                <textarea
                  {...patientForm.register("address")}
                  rows={3}
                  className="w-full rounded-lg border border-pink-300/35 bg-matte-800 px-3 py-2 text-sm text-slate-100 outline-none focus:border-neon-pink/70"
                />
              </div>

              <label className="flex items-center gap-2 text-sm text-slate-300">
                <input type="checkbox" {...patientForm.register("whatsapp_opt_in")} />
                WhatsApp opt-in
              </label>

              <VisitFields
                title="Start Visit"
                branchLabel={activeShop?.locationLabel || activeShop?.name || "Selected branch"}
                register={patientForm.register}
                errors={patientForm.formState.errors}
              />

              <div className="flex flex-wrap gap-2">
                <button
                  type="submit"
                  disabled={isSaving}
                  className="inline-flex items-center gap-2 rounded-lg border border-emerald-300/45 bg-emerald-400/15 px-4 py-2 text-sm font-medium text-emerald-50 disabled:opacity-60"
                >
                  <ChevronRight size={16} />
                  Register Patient & Start Visit
                </button>
                <button
                  type="button"
                  onClick={() => setMode("search")}
                  className="rounded-lg border border-slate-500/45 px-4 py-2 text-sm font-medium text-slate-200"
                >
                  Cancel
                </button>
              </div>
            </form>
          )}

          {mode === "start-visit" && selectedPatient && (
            <form className="space-y-5" onSubmit={visitForm.handleSubmit(onStartVisit)}>
              <div>
                <h3 className="text-lg font-semibold text-slate-100">Start Visit</h3>
                <div className="mt-2 rounded-xl border border-pink-300/20 bg-matte-800/65 p-3 text-sm text-slate-200">
                  <p className="font-semibold text-pink-100">{selectedPatient.name}</p>
                  <p>{selectedPatient.customer_id}</p>
                  <p>{selectedPatient.contact_no}</p>
                </div>
              </div>

              <VisitFields
                title="Visit Details"
                branchLabel={activeShop?.locationLabel || activeShop?.name || "Selected branch"}
                register={visitForm.register}
                errors={visitForm.formState.errors}
              />

              <div className="flex flex-wrap gap-2">
                <button
                  type="submit"
                  disabled={createVisitMutation.isPending}
                  className="inline-flex items-center gap-2 rounded-lg border border-emerald-300/45 bg-emerald-400/15 px-4 py-2 text-sm font-medium text-emerald-50 disabled:opacity-60"
                >
                  <CalendarPlus size={16} />
                  Continue Visit
                </button>
                <button
                  type="button"
                  onClick={() => navigate(`${CRM_PATHS.customerRecords}?q=${encodeURIComponent(selectedPatient.customer_id)}`)}
                  className="rounded-lg border border-pink-300/35 px-4 py-2 text-sm font-medium text-pink-100"
                >
                  View History
                </button>
              </div>
            </form>
          )}

          {mode === "search" && (
            <div className="space-y-4 text-sm text-slate-300">
              <h3 className="text-lg font-semibold text-slate-100">Visit Context</h3>
              {selectedPatient ? (
                <div className="rounded-xl border border-pink-300/20 bg-matte-800/65 p-4">
                  <p className="font-semibold text-pink-100">{selectedPatient.name}</p>
                  <p className="mt-1">{selectedPatient.customer_id}</p>
                  <p>{selectedPatient.contact_no}</p>
                  <div className="mt-3 flex flex-wrap gap-2">
                    <button
                      type="button"
                      onClick={() => openVisitForPatient(selectedPatient)}
                      className="inline-flex items-center gap-2 rounded-lg border border-emerald-300/35 bg-emerald-400/10 px-3 py-2 text-sm font-medium text-emerald-100"
                    >
                      <CalendarPlus size={16} />
                      Start Visit
                    </button>
                    <button
                      type="button"
                      onClick={() => navigate(`${CRM_PATHS.customerRecords}?q=${encodeURIComponent(selectedPatient.customer_id)}`)}
                      className="rounded-lg border border-slate-500/45 px-3 py-2 text-sm font-medium text-slate-200"
                    >
                      History
                    </button>
                  </div>
                </div>
              ) : (
                <p className="rounded-lg border border-dashed border-slate-600 p-5">
                  Select a search result or register a new patient to start a visit.
                </p>
              )}
            </div>
          )}
        </section>
      </div>
    </div>
  );
}

type VisitFieldProps<T extends VisitFormValues | PatientVisitFormValues> = {
  title: string;
  branchLabel: string;
  register: ReturnType<typeof useForm<T>>["register"];
  errors: ReturnType<typeof useForm<T>>["formState"]["errors"];
};

function VisitFields<T extends VisitFormValues | PatientVisitFormValues>({
  title,
  branchLabel,
  register,
  errors
}: VisitFieldProps<T>) {
  return (
    <div className="space-y-3 rounded-xl border border-pink-300/20 bg-matte-800/65 p-4">
      <div className="flex flex-col gap-1 sm:flex-row sm:items-center sm:justify-between">
        <h4 className="font-semibold text-slate-100">{title}</h4>
        <span className="text-xs text-slate-400">Branch: {branchLabel}</span>
      </div>

      <div className="grid gap-3 md:grid-cols-2">
        <div>
          <label className="mb-1 block text-xs font-medium uppercase tracking-wide text-slate-300">Visit Date</label>
          <input
            type="datetime-local"
            {...register("visit_date" as never)}
            className="h-11 w-full rounded-lg border border-pink-300/35 bg-matte-850 px-3 text-sm text-slate-100 outline-none focus:border-neon-pink/70"
          />
          {errors.visit_date && <p className="mt-1 text-xs text-rose-300">{String(errors.visit_date.message)}</p>}
        </div>
        <div>
          <label className="mb-1 block text-xs font-medium uppercase tracking-wide text-slate-300">Visit Status</label>
          <select
            {...register("visit_status" as never)}
            className="h-11 w-full rounded-lg border border-pink-300/35 bg-matte-850 px-3 text-sm text-slate-100 outline-none focus:border-neon-pink/70"
          >
            <option value="draft">Draft</option>
            <option value="in_progress">In progress</option>
          </select>
        </div>
      </div>

      <div className="grid gap-3 md:grid-cols-2">
        <div>
          <label className="mb-1 block text-xs font-medium uppercase tracking-wide text-slate-300">Reason For Visit</label>
          <input
            {...register("reason_for_visit" as never)}
            className="h-11 w-full rounded-lg border border-pink-300/35 bg-matte-850 px-3 text-sm text-slate-100 outline-none focus:border-neon-pink/70"
          />
          {errors.reason_for_visit && (
            <p className="mt-1 text-xs text-rose-300">{String(errors.reason_for_visit.message)}</p>
          )}
        </div>
        <div>
          <label className="mb-1 block text-xs font-medium uppercase tracking-wide text-slate-300">Referred By</label>
          <input
            {...register("referred_by" as never)}
            className="h-11 w-full rounded-lg border border-pink-300/35 bg-matte-850 px-3 text-sm text-slate-100 outline-none focus:border-neon-pink/70"
          />
        </div>
      </div>

      <div>
        <label className="mb-1 block text-xs font-medium uppercase tracking-wide text-slate-300">Visit Notes</label>
        <textarea
          {...register("visit_notes" as never)}
          rows={3}
          className="w-full rounded-lg border border-pink-300/35 bg-matte-850 px-3 py-2 text-sm text-slate-100 outline-none focus:border-neon-pink/70"
        />
      </div>

      <p className="text-xs text-slate-400">Assigned examiner defaults to the logged-in staff member unless admin assigns later.</p>
    </div>
  );
}
