import {
  ArrowRight,
  BadgeCheck,
  CalendarCheck,
  CheckCircle2,
  Crown,
  Eye,
  Gem,
  Glasses,
  HeartHandshake,
  MapPin,
  Phone,
  Search,
  ShieldCheck,
  Sparkles,
  Star,
  Store,
  Trophy,
  UsersRound
} from "lucide-react";
import type { LucideIcon } from "lucide-react";
import type { FormEvent, ReactNode } from "react";
import { useMemo, useState } from "react";

import { PublicFooter } from "@/components/public/PublicFooter";
import { PublicHeader } from "@/components/public/PublicHeader";

type CollectionFilter = "all" | "prescription" | "sunglasses" | "kids" | "designer" | "contact";

const tickerItems = [
  "Established 1985",
  "4 Specialized Centers",
  "3 Generations of Trust",
  "Premium Branded Eyewear",
  "Expert Eye Examinations",
  "Designer Frames & Sunglasses",
  "Serving Kalyan Since 1985"
];

const centers = [
  {
    name: "Adarsh Optical Centre",
    location: "Kalyan",
    icon: Glasses,
    detail: "One of Kalyan's trusted optical destinations, known for quality eyewear, expert guidance, and customer-first service."
  },
  {
    name: "Adarsh Optometric Clinic",
    location: "Khadakpada, Kalyan West",
    icon: Eye,
    detail: "Comprehensive eye examinations, vision assessments, and personalized eye care solutions in a professional clinic environment."
  },
  {
    name: "Adarsh Opticals",
    location: "Near Muxar Hospital",
    icon: Store,
    detail: "Conveniently located near Muxar Hospital, serving the community with premium eyewear and professional optical services."
  },
  {
    name: "Adarsh Eye Boutique",
    location: "Kalyan",
    icon: Crown,
    detail: "A modern eyewear destination offering premium brands, designer collections, luxury sunglasses, and personal styling."
  }
];

const stats = [
  { value: "40+", label: "Years of Trust" },
  { value: "4", label: "Specialized Centers" },
  { value: "3", label: "Generations" },
  { value: "10K+", label: "Happy Customers" }
];

const filterTabs: Array<{ id: CollectionFilter; label: string }> = [
  { id: "all", label: "All Frames" },
  { id: "prescription", label: "Prescription" },
  { id: "sunglasses", label: "Sunglasses" },
  { id: "kids", label: "Kids" },
  { id: "designer", label: "Designer" },
  { id: "contact", label: "Contact Lenses" }
];

const products: Array<{
  name: string;
  category: string;
  filters: CollectionFilter[];
  badge: string;
  description: string;
  Icon: LucideIcon;
  tone: string;
}> = [
  {
    name: "Everyday Comfort Frames",
    category: "Prescription",
    filters: ["prescription"],
    badge: "NEW",
    description: "Price placeholder - add brand and model details.",
    Icon: Glasses,
    tone: "from-[#dbeafe] via-white to-[#c7d2fe]"
  },
  {
    name: "UV Protected Sunglasses",
    category: "Sunglasses",
    filters: ["sunglasses"],
    badge: "BESTSELLER",
    description: "Price placeholder - add brand and lens type.",
    Icon: ShieldCheck,
    tone: "from-[#0a1f5c] via-[#1549a8] to-[#0f172a]"
  },
  {
    name: "Luxury Designer Collection",
    category: "Designer",
    filters: ["designer"],
    badge: "LUXURY",
    description: "Price placeholder - add premium brand details.",
    Icon: Gem,
    tone: "from-[#fff7cc] via-white to-[#ffd700]"
  },
  {
    name: "Durable Kids Eyewear",
    category: "Kids",
    filters: ["kids"],
    badge: "KIDS",
    description: "Price placeholder - add safety and fit details.",
    Icon: Sparkles,
    tone: "from-[#dcfce7] via-white to-[#bfdbfe]"
  },
  {
    name: "Blue-Cut Lens Solutions",
    category: "Prescription",
    filters: ["prescription"],
    badge: "LIGHTWEIGHT",
    description: "Price placeholder - add lens brand and coating.",
    Icon: Eye,
    tone: "from-[#eff6ff] via-white to-[#bae6fd]"
  },
  {
    name: "Fashion Statement Frames",
    category: "Designer Sunglasses",
    filters: ["designer", "sunglasses"],
    badge: "STYLE",
    description: "Price placeholder - add collection details.",
    Icon: Crown,
    tone: "from-[#fce7f3] via-white to-[#fed7aa]"
  },
  {
    name: "Daily & Monthly Lenses",
    category: "Contact Lenses",
    filters: ["contact"],
    badge: "CLEAR VISION",
    description: "Price placeholder - add lens type and guidance.",
    Icon: Eye,
    tone: "from-[#ecfdf5] via-white to-[#bbf7d0]"
  },
  {
    name: "Premium Metal Frames",
    category: "Designer",
    filters: ["designer"],
    badge: "PREMIUM",
    description: "Price placeholder - add brand and finish details.",
    Icon: BadgeCheck,
    tone: "from-[#e0e7ff] via-white to-[#fef3c7]"
  }
];

const features = [
  {
    title: "40+ Years of Trust",
    body: "A legacy built through decades of reliable service, professional care, and customer satisfaction.",
    icon: Trophy
  },
  {
    title: "Expert Eye Care",
    body: "Comprehensive eye examinations and personalized recommendations for every customer.",
    icon: Eye
  },
  {
    title: "Authentic Brands",
    body: "Trusted branded frames, sunglasses, and lenses from recognized eyewear companies.",
    icon: CheckCircle2
  },
  {
    title: "Generational Relationships",
    body: "Serving families across generations with transparency, guidance, and dependable care.",
    icon: HeartHandshake
  },
  {
    title: "Premium Boutique",
    body: "Modern eyewear styling and luxury collections for customers who want a premium look.",
    icon: Gem
  },
  {
    title: "4 Convenient Locations",
    body: "Specialized centers across Kalyan for eye tests, eyewear shopping, and boutique experiences.",
    icon: MapPin
  }
];

const services = [
  {
    title: "Comprehensive Eye Exams",
    body: "Professional vision testing and eye assessment for accurate prescriptions and better eye health.",
    icon: Search
  },
  {
    title: "Frame Fitting & Styling",
    body: "Personalized eyewear styling to suit your face shape, comfort needs, and daily lifestyle.",
    icon: Glasses
  },
  {
    title: "Lens Consultation",
    body: "Expert recommendations for lens type, coatings, protection, and visual comfort.",
    icon: Eye
  },
  {
    title: "Children's Eye Care",
    body: "Friendly guidance for children's spectacles, first glasses, fit, comfort, and durability.",
    icon: UsersRound
  }
];

const testimonials = [
  {
    quote:
      "Adarsh Optical Group has been our family's trusted optical store for years. Their guidance, service, and product quality are excellent.",
    name: "Customer Name",
    meta: "Customer since 2012 - Kalyan West"
  },
  {
    quote:
      "The eye test was detailed, the staff explained lenses properly, and the frame selection felt premium and comfortable.",
    name: "Customer Name",
    meta: "Customer since 2018 - Khadakpada"
  },
  {
    quote:
      "I found the perfect sunglasses at Adarsh Eye Boutique. The styling support made the whole experience very personal.",
    name: "Customer Name",
    meta: "Customer since 2023 - Kalyan"
  }
];

export function PublicHomePage() {
  const [activeFilter, setActiveFilter] = useState<CollectionFilter>("all");
  const [submitted, setSubmitted] = useState(false);

  const visibleProducts = useMemo(() => {
    if (activeFilter === "all") {
      return products;
    }

    return products.filter((product) => product.filters.includes(activeFilter));
  }, [activeFilter]);

  const handleContactSubmit = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    setSubmitted(true);
  };

  return (
    <div className="min-h-screen bg-[#f6f8ff] text-[#0a1228]">
      <PublicHeader />

      <div className="overflow-hidden bg-[#071a4a] py-2 text-xs font-semibold uppercase text-white" aria-label="Brand highlights">
        <div className="website-ticker-track flex w-max items-center gap-8">
          {[...tickerItems, ...tickerItems].map((item, index) => (
            <span key={`${item}-${index}`} className="inline-flex items-center gap-8">
              {item}
              <span className="h-1.5 w-1.5 rounded-full bg-[#ffd700]" aria-hidden="true" />
            </span>
          ))}
        </div>
      </div>

      <main>
        <section id="home" className="relative overflow-hidden bg-[#0a1f5c] text-white">
          <div className="absolute inset-x-0 bottom-0 h-24 bg-white" aria-hidden="true" />
          <div className="relative mx-auto grid min-h-[calc(100vh-92px)] max-w-7xl items-center gap-10 px-4 py-12 sm:px-6 lg:grid-cols-[1.02fr_0.98fr] lg:px-8 lg:py-16">
            <div className="max-w-3xl">
              <p className="inline-flex items-center gap-2 rounded-full border border-white/20 bg-white/10 px-4 py-2 text-xs font-semibold uppercase text-[#f8e58a]">
                <Sparkles size={15} />
                Trusted Since 1985 - Kalyan, Maharashtra
              </p>
              <h1 className="mt-5 text-4xl font-bold leading-tight text-white sm:text-5xl lg:text-6xl">
                See Better. Look Better. <span className="text-[#ffd700]">Live Better.</span>
              </h1>
              <p className="mt-5 max-w-2xl text-base leading-7 text-blue-50 sm:text-lg">
                For over 40 years, Adarsh Optical Group has been one of Kalyan's most trusted names in professional eye
                care, authentic branded eyewear, designer frames, and personalized optical service across four specialized
                centers.
              </p>
              <div className="mt-8 flex flex-col gap-3 sm:flex-row">
                <a
                  href="#contact"
                  className="inline-flex items-center justify-center gap-2 rounded-full bg-[#ffd700] px-5 py-3 text-sm font-bold text-[#071a4a] shadow-lg shadow-black/20 transition hover:-translate-y-0.5 hover:bg-[#ffe66c]"
                >
                  <CalendarCheck size={18} />
                  Book Free Eye Test
                </a>
                <a
                  href="#collections"
                  className="inline-flex items-center justify-center gap-2 rounded-full border border-white/35 bg-white/10 px-5 py-3 text-sm font-bold text-white transition hover:-translate-y-0.5 hover:bg-white/20"
                >
                  Explore Collections
                  <ArrowRight size={18} />
                </a>
              </div>
              <div className="mt-8 flex flex-wrap gap-3 text-sm font-semibold text-blue-50">
                <span className="rounded-full border border-white/15 bg-white/10 px-4 py-2">Premium eyewear</span>
                <span className="rounded-full border border-white/15 bg-white/10 px-4 py-2">Expert guidance</span>
                <span className="rounded-full border border-white/15 bg-white/10 px-4 py-2">Family legacy</span>
              </div>
            </div>

            <div className="relative pb-16 lg:pb-0" aria-label="Premium eyewear showcase">
              <div className="relative overflow-hidden rounded-[28px] border border-white/20 bg-white p-4 text-[#0a1228] shadow-2xl shadow-black/25">
                <div className="grid min-h-[340px] place-items-center rounded-2xl bg-gradient-to-br from-[#eaf3ff] via-white to-[#ffd700]/35 p-6">
                  <div className="text-center">
                    <div className="mx-auto grid h-28 w-28 place-items-center rounded-full border border-[#1549a8]/20 bg-white shadow-xl">
                      <Glasses className="text-[#1549a8]" size={58} />
                    </div>
                    <strong className="mt-6 block text-lg text-[#0a1f5c]">Upload Premium Eyewear / Store Photo Here</strong>
                    <small className="mt-2 block text-sm font-medium text-slate-500">Recommended size: 700 x 520px</small>
                  </div>
                </div>
                <div className="mt-4 flex flex-col justify-between gap-4 rounded-lg bg-[#f6f8ff] p-4 sm:flex-row sm:items-center">
                  <div>
                    <h2 className="text-lg font-bold text-[#0a1f5c]">Professional Eye Care Meets Modern Eyewear Styling</h2>
                    <p className="mt-1 text-sm leading-6 text-slate-600">
                      Use this area for a polished clinic, boutique, or frame display photo.
                    </p>
                  </div>
                  <span className="inline-flex rounded-full bg-[#0a1f5c] px-4 py-2 text-xs font-bold uppercase text-[#ffd700]">
                    Since 1985
                  </span>
                </div>
              </div>

              <div className="website-float absolute -bottom-1 right-3 max-w-[290px] rounded-lg border border-[#ffd700]/50 bg-white p-4 text-[#0a1228] shadow-xl lg:-bottom-8 lg:right-10">
                <strong className="block text-[#0a1f5c]">4 Specialized Centers</strong>
                <span className="mt-1 block text-sm leading-5 text-slate-600">
                  Clinical eye care, premium frames, lenses, sunglasses, and boutique collections.
                </span>
              </div>
            </div>

            <div className="relative z-10 grid gap-3 sm:grid-cols-2 lg:col-span-2 lg:grid-cols-4">
              {stats.map((stat) => (
                <article key={stat.label} className="rounded-lg border border-white/15 bg-white p-5 text-center text-[#0a1f5c] shadow-lg">
                  <span className="text-3xl font-extrabold">{stat.value}</span>
                  <p className="mt-1 text-sm font-semibold text-slate-600">{stat.label}</p>
                </article>
              ))}
            </div>
          </div>
        </section>

        <section id="about" className="bg-white px-4 py-16 sm:px-6 lg:px-8">
          <div className="mx-auto grid max-w-7xl gap-10 lg:grid-cols-[0.85fr_1.15fr] lg:items-center">
            <div className="relative rounded-lg border border-[#d8e4ff] bg-gradient-to-br from-[#f6f8ff] to-white p-5 shadow-xl shadow-blue-950/10">
              <div className="grid min-h-[360px] place-items-center rounded-lg border border-dashed border-[#1549a8]/30 bg-white">
                <div className="text-center">
                  <Store className="mx-auto text-[#1549a8]" size={56} />
                  <strong className="mt-4 block text-[#0a1f5c]">Upload Your Store Photo Here</strong>
                  <span className="mt-1 block text-sm text-slate-500">Recommended size: 600 x 400px</span>
                </div>
              </div>
              <div className="absolute -bottom-5 right-7 rounded-lg bg-[#ffd700] px-5 py-4 text-[#071a4a] shadow-lg">
                <span className="block text-xs font-bold uppercase">Since</span>
                <b className="text-2xl">1985</b>
              </div>
            </div>

            <div>
              <SectionIntro
                eyebrow="Our Story"
                title="A legacy of vision care built on trust, expertise, and family values."
                body="Established in 1985, Adarsh Optical Group began with a simple yet powerful vision - to provide reliable eye care services and premium optical solutions to every customer who walks through our doors."
              />
              <p className="mt-5 text-base leading-8 text-slate-600">
                What started as a single optical store has grown into four specialized centers serving generations of
                families across Kalyan. Founded by Mr. Vinayak A. Dabholkar and Mr. Bipin A. Dabholkar, the legacy was
                carried forward by Mr. Vipul Dabholkar and Mr. Omkar Dabholkar, and today continues under the leadership
                of Mrs. Neha Vipul Dabholkar.
              </p>
              <div className="mt-6 flex flex-wrap gap-3">
                {["40+ Years Trusted", "4 Centers in Kalyan", "Family Legacy", "Certified Optometrists"].map((item) => (
                  <span key={item} className="rounded-full border border-[#d8e4ff] bg-[#f6f8ff] px-4 py-2 text-sm font-bold text-[#1549a8]">
                    {item}
                  </span>
                ))}
              </div>
            </div>
          </div>
        </section>

        <section id="centers" className="bg-[#f6f8ff] px-4 py-16 sm:px-6 lg:px-8">
          <div className="mx-auto max-w-7xl">
            <SectionHeading
              eyebrow="Our Presence"
              title="Four Specialized Centers"
              body="Each Adarsh center is designed to serve a specific eye care and eyewear need - from clinical vision assessment to luxury designer eyewear."
            />

            <div className="mt-10 grid gap-5 md:grid-cols-2">
              {centers.map((center, index) => (
                <article
                  key={center.name}
                  className="rounded-lg border border-[#d8e4ff] bg-white p-6 shadow-lg shadow-blue-950/5 transition hover:-translate-y-1 hover:shadow-xl"
                >
                  <div className="flex items-start gap-4">
                    <span className="grid h-14 w-14 shrink-0 place-items-center rounded-lg bg-[#0a1f5c] text-[#ffd700]">
                      <center.icon size={28} />
                    </span>
                    <div>
                      <h3 className="text-xl font-bold text-[#0a1f5c]">{center.name}</h3>
                      <p className="mt-3 text-sm leading-6 text-slate-600">{center.detail}</p>
                      <span className="mt-4 inline-flex items-center gap-2 rounded-full bg-[#fff8d6] px-3 py-1.5 text-xs font-bold text-[#0a1f5c]">
                        <MapPin size={14} />
                        {center.location}
                      </span>
                    </div>
                  </div>
                  {index >= 2 ? <div className="mt-5 h-1 rounded-full bg-[#ffd700]" aria-hidden="true" /> : null}
                </article>
              ))}
            </div>
          </div>
        </section>

        <section id="collections" className="bg-white px-4 py-16 sm:px-6 lg:px-8">
          <div className="mx-auto max-w-7xl">
            <SectionHeading
              eyebrow="Eyewear Collections"
              title="Find Your Perfect Frame"
              body="Showcase prescription frames, sunglasses, kids eyewear, designer collections, and contact lenses with real product photos later."
            />

            <div className="mt-8 flex flex-wrap justify-center gap-2" aria-label="Collection filter tabs">
              {filterTabs.map((tab) => {
                const isActive = activeFilter === tab.id;

                return (
                  <button
                    key={tab.id}
                    type="button"
                    aria-pressed={isActive}
                    onClick={() => setActiveFilter(tab.id)}
                    className={`rounded-full border px-4 py-2 text-sm font-bold transition ${
                      isActive
                        ? "border-[#0a1f5c] bg-[#0a1f5c] text-white"
                        : "border-[#d8e4ff] bg-[#f6f8ff] text-[#0a1f5c] hover:border-[#1549a8]"
                    }`}
                  >
                    {tab.label}
                  </button>
                );
              })}
            </div>

            <div className="mt-10 grid gap-5 sm:grid-cols-2 lg:grid-cols-4">
              {visibleProducts.map((product) => (
                <article key={product.name} className="overflow-hidden rounded-lg border border-[#d8e4ff] bg-white shadow-lg shadow-blue-950/5">
                  <div className={`relative grid aspect-square place-items-center bg-gradient-to-br ${product.tone} p-5`}>
                    <span className="absolute left-4 top-4 rounded-full bg-white/90 px-3 py-1 text-xs font-extrabold text-[#0a1f5c] shadow">
                      {product.badge}
                    </span>
                    <div className="text-center">
                      <product.Icon className="mx-auto text-[#1549a8]" size={54} />
                      <strong className="mt-4 block text-sm text-[#0a1f5c]">Add Product Photo Here</strong>
                      <small className="mt-1 block text-xs text-slate-500">Recommended: 600 x 600px</small>
                    </div>
                  </div>
                  <div className="p-5">
                    <div className="text-xs font-extrabold uppercase text-[#1549a8]">{product.category}</div>
                    <h3 className="mt-2 text-lg font-bold text-[#0a1f5c]">{product.name}</h3>
                    <p className="mt-2 text-sm leading-6 text-slate-600">{product.description}</p>
                  </div>
                </article>
              ))}
            </div>

            <div className="mt-10 text-center">
              <a
                href="#contact"
                className="inline-flex items-center justify-center gap-2 rounded-full bg-[#1549a8] px-5 py-3 text-sm font-bold text-white transition hover:-translate-y-0.5 hover:bg-[#0a1f5c]"
              >
                View Full Collection
                <ArrowRight size={17} />
              </a>
            </div>
          </div>
        </section>

        <section id="why-us" className="bg-[#071a4a] px-4 py-16 text-white sm:px-6 lg:px-8">
          <div className="mx-auto max-w-7xl">
            <SectionHeading
              eyebrow="Why Choose Us"
              title="What Makes Us Different"
              body="At Adarsh Optical Group, eyewear is more than a visual aid - it is vision, comfort, confidence, and personal style."
              inverted
            />

            <div className="mt-10 grid gap-5 sm:grid-cols-2 lg:grid-cols-3">
              {features.map((feature) => (
                <article key={feature.title} className="rounded-lg border border-white/15 bg-white/10 p-6">
                  <feature.icon className="text-[#ffd700]" size={30} />
                  <h3 className="mt-4 text-lg font-bold">{feature.title}</h3>
                  <p className="mt-2 text-sm leading-6 text-blue-50">{feature.body}</p>
                </article>
              ))}
            </div>
          </div>
        </section>

        <section id="legacy" className="bg-white px-4 py-16 sm:px-6 lg:px-8">
          <div className="mx-auto max-w-7xl rounded-lg bg-gradient-to-br from-[#0a1f5c] to-[#1549a8] p-6 text-white shadow-2xl shadow-blue-950/20 sm:p-8 lg:p-10">
            <div className="grid gap-8 lg:grid-cols-[0.85fr_1.15fr]">
              <div>
                <h2 className="text-3xl font-bold leading-tight sm:text-4xl">
                  Three Generations, <span className="text-[#ffd700]">One Unwavering Vision.</span>
                </h2>
                <p className="mt-4 text-base leading-7 text-blue-50">
                  The Adarsh Optical Group legacy continues with the same commitment to quality, trust, and customer-first
                  eye care that began in 1985.
                </p>
                <span className="mt-6 inline-flex rounded-full bg-white px-4 py-2 text-sm font-bold text-[#0a1f5c]">
                  Seeing Better. Looking Better. Living Better.
                </span>
              </div>

              <div className="space-y-4">
                {[
                  {
                    title: "Gen 1 - Founders, 1985",
                    body:
                      "Mr. Vinayak A. Dabholkar and Mr. Bipin A. Dabholkar founded the legacy with a strong focus on quality and customer satisfaction."
                  },
                  {
                    title: "Gen 2 - Expansion & Growth",
                    body:
                      "Mr. Vipul Dabholkar and Mr. Omkar Dabholkar strengthened the group's presence and embraced advancements in optical technology."
                  },
                  {
                    title: "Gen 3 - Present Leadership",
                    body:
                      "Mrs. Neha Vipul Dabholkar continues the family values while shaping the future of eye care and optical retail."
                  }
                ].map((item, index) => (
                  <article key={item.title} className="flex gap-4 rounded-lg bg-white p-4 text-[#0a1228]">
                    <div className="grid h-10 w-10 shrink-0 place-items-center rounded-full bg-[#ffd700] text-sm font-extrabold text-[#071a4a]">
                      {index + 1}
                    </div>
                    <div>
                      <h3 className="font-bold text-[#0a1f5c]">{item.title}</h3>
                      <p className="mt-1 text-sm leading-6 text-slate-600">{item.body}</p>
                    </div>
                  </article>
                ))}
              </div>
            </div>
          </div>
        </section>

        <section id="services" className="bg-white px-4 pb-16 sm:px-6 lg:px-8">
          <div className="mx-auto max-w-7xl">
            <SectionHeading
              eyebrow="Our Services"
              title="Complete Eye Care & Eyewear Services"
              body="Professional guidance for your vision, comfort, lifestyle, and eyewear preferences."
            />

            <div className="mt-10 grid gap-5 sm:grid-cols-2 lg:grid-cols-4">
              {services.map((service) => (
                <article key={service.title} className="rounded-lg border border-[#d8e4ff] bg-[#f6f8ff] p-6">
                  <service.icon className="text-[#1549a8]" size={30} />
                  <h3 className="mt-4 text-lg font-bold text-[#0a1f5c]">{service.title}</h3>
                  <p className="mt-2 text-sm leading-6 text-slate-600">{service.body}</p>
                </article>
              ))}
            </div>
          </div>
        </section>

        <section id="testimonials" className="bg-[#f6f8ff] px-4 py-16 sm:px-6 lg:px-8">
          <div className="mx-auto max-w-7xl">
            <SectionHeading
              eyebrow="Testimonials"
              title="What Families Say About Us"
              body="Replace these placeholders with real customer reviews from Google, WhatsApp, or in-store feedback."
            />

            <div className="mt-10 grid gap-5 md:grid-cols-3">
              {testimonials.map((testimonial) => (
                <article key={testimonial.meta} className="rounded-lg border border-[#d8e4ff] bg-white p-6 shadow-lg shadow-blue-950/5">
                  <div className="flex gap-1 text-[#ffd700]" aria-label="Five star rating">
                    {Array.from({ length: 5 }).map((_, index) => (
                      <Star key={index} size={17} fill="currentColor" />
                    ))}
                  </div>
                  <blockquote className="mt-4 text-sm leading-7 text-slate-700">"{testimonial.quote}"</blockquote>
                  <h3 className="mt-5 font-bold text-[#0a1f5c]">{testimonial.name}</h3>
                  <p className="mt-1 text-xs font-semibold text-slate-500">{testimonial.meta}</p>
                </article>
              ))}
            </div>
          </div>
        </section>

        <section id="book" className="bg-[#ffd700] px-4 py-12 text-[#071a4a] sm:px-6 lg:px-8">
          <div className="mx-auto flex max-w-7xl flex-col gap-6 lg:flex-row lg:items-center lg:justify-between">
            <div>
              <h2 className="text-3xl font-extrabold sm:text-4xl">Ready to See the World More Clearly?</h2>
              <p className="mt-3 max-w-2xl text-sm font-semibold leading-6 text-[#0a1f5c]">
                Book an eye examination, explore premium eyewear, or visit your nearest Adarsh Optical Group center in
                Kalyan.
              </p>
            </div>
            <div className="flex flex-col gap-3 sm:flex-row">
              <a className="inline-flex items-center justify-center gap-2 rounded-full bg-[#071a4a] px-5 py-3 text-sm font-bold text-white" href="#contact">
                <CalendarCheck size={18} />
                Book Free Eye Test
              </a>
              <a
                className="inline-flex items-center justify-center gap-2 rounded-full border border-[#071a4a]/35 px-5 py-3 text-sm font-bold text-[#071a4a]"
                href="#contact"
              >
                <Phone size={18} />
                Call Us Now
              </a>
              <a
                className="inline-flex items-center justify-center gap-2 rounded-full border border-[#071a4a]/35 px-5 py-3 text-sm font-bold text-[#071a4a]"
                href="#centers"
              >
                <MapPin size={18} />
                Find Nearest Center
              </a>
            </div>
          </div>
        </section>

        <section id="contact" className="bg-white px-4 py-16 sm:px-6 lg:px-8">
          <div className="mx-auto max-w-7xl">
            <SectionHeading
              eyebrow="Contact Us"
              title="Visit Your Nearest Adarsh Center"
              body="Use the form layout below for booking requests, callbacks, and customer inquiries."
            />

            <div className="mt-10 grid gap-6 lg:grid-cols-[1.1fr_0.9fr]">
              <div className="rounded-lg border border-[#d8e4ff] bg-[#f6f8ff] p-6">
                <h3 className="text-xl font-bold text-[#0a1f5c]">Request a Callback</h3>
                <form className="mt-5 space-y-4" onSubmit={handleContactSubmit}>
                  <div className="grid gap-4 sm:grid-cols-2">
                    <FormField label="Name" id="name">
                      <input id="name" name="name" type="text" placeholder="Your name" required />
                    </FormField>
                    <FormField label="Phone Number" id="phone">
                      <input id="phone" name="phone" type="tel" placeholder="+91 XXXXX XXXXX" required />
                    </FormField>
                  </div>
                  <div className="grid gap-4 sm:grid-cols-2">
                    <FormField label="Service Required" id="service">
                      <select id="service" name="service">
                        <option>Book Eye Test</option>
                        <option>Prescription Glasses</option>
                        <option>Sunglasses</option>
                        <option>Contact Lenses</option>
                        <option>Designer Frames</option>
                      </select>
                    </FormField>
                    <FormField label="Preferred Center" id="center">
                      <select id="center" name="center">
                        {centers.map((center) => (
                          <option key={center.name}>{center.name}</option>
                        ))}
                      </select>
                    </FormField>
                  </div>
                  <FormField label="Message" id="message">
                    <textarea id="message" name="message" placeholder="Tell us what you are looking for..." rows={5} />
                  </FormField>
                  <button
                    className="inline-flex items-center justify-center gap-2 rounded-full bg-[#1549a8] px-5 py-3 text-sm font-bold text-white transition hover:bg-[#0a1f5c]"
                    type="submit"
                  >
                    Submit Request
                    <ArrowRight size={17} />
                  </button>
                  {submitted ? (
                    <p className="text-sm font-semibold text-[#1549a8]" role="status">
                      Thank you. This website form is ready for backend or WhatsApp connection.
                    </p>
                  ) : null}
                </form>
              </div>

              <div className="rounded-lg border border-[#d8e4ff] bg-white p-6 shadow-lg shadow-blue-950/5">
                <h3 className="text-xl font-bold text-[#0a1f5c]">Our Centers</h3>
                <div className="mt-5 space-y-4">
                  {centers.map((center) => (
                    <div key={center.name} className="rounded-lg border border-[#d8e4ff] bg-[#f6f8ff] p-4">
                      <strong className="block text-[#0a1f5c]">{center.name}</strong>
                      <span className="mt-2 flex items-center gap-2 text-sm text-slate-600">
                        <MapPin size={15} />
                        {center.location}
                      </span>
                      <span className="mt-1 flex items-center gap-2 text-sm text-slate-600">
                        <Phone size={15} />
                        Phone placeholder
                      </span>
                    </div>
                  ))}
                </div>
              </div>
            </div>
          </div>
        </section>
      </main>

      <PublicFooter />

      <div className="fixed bottom-5 right-5 z-40 flex flex-col gap-3">
        <button
          type="button"
          onClick={() => window.scrollTo({ top: 0, behavior: "smooth" })}
          className="grid h-12 w-12 place-items-center rounded-full bg-[#0a1f5c] text-white shadow-lg"
          aria-label="Back to top"
        >
          <ArrowRight className="-rotate-90" size={20} />
        </button>
        <a
          href="#contact"
          className="grid h-12 w-12 place-items-center rounded-full bg-[#25d366] text-white shadow-lg"
          aria-label="Contact on WhatsApp"
        >
          <Phone size={20} />
        </a>
      </div>
    </div>
  );
}

function SectionIntro({ eyebrow, title, body }: { eyebrow: string; title: string; body: string }) {
  return (
    <div>
      <span className="text-sm font-extrabold uppercase text-[#1549a8]">{eyebrow}</span>
      <h2 className="mt-3 text-3xl font-extrabold leading-tight text-[#0a1f5c] sm:text-4xl">{title}</h2>
      <p className="mt-4 text-base leading-8 text-slate-600">{body}</p>
    </div>
  );
}

function SectionHeading({
  eyebrow,
  title,
  body,
  inverted = false
}: {
  eyebrow: string;
  title: string;
  body: string;
  inverted?: boolean;
}) {
  return (
    <div className="mx-auto max-w-3xl text-center">
      <span className={`text-sm font-extrabold uppercase ${inverted ? "text-[#ffd700]" : "text-[#1549a8]"}`}>{eyebrow}</span>
      <h2 className={`mt-3 text-3xl font-extrabold leading-tight sm:text-4xl ${inverted ? "text-white" : "text-[#0a1f5c]"}`}>
        {title}
      </h2>
      <p className={`mt-4 text-base leading-7 ${inverted ? "text-blue-50" : "text-slate-600"}`}>{body}</p>
      <div className="mx-auto mt-5 h-1 w-20 rounded-full bg-[#ffd700]" aria-hidden="true" />
    </div>
  );
}

function FormField({ children, id, label }: { children: ReactNode; id: string; label: string }) {
  return (
    <div>
      <label className="mb-2 block text-sm font-bold text-[#0a1f5c]" htmlFor={id}>
        {label}
      </label>
      {children}
    </div>
  );
}
