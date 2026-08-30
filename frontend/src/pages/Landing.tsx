import { Link } from 'react-router-dom'
import {
  ArrowRight, BarChart3, Bot, Check, Code2, Cpu, FileText, Github, Globe,
  Instagram, Layers, Mail, MessageCircle, MessageSquare, ShieldCheck, Slack,
  Sparkles, UserCheck, Wand2, Workflow, Zap,
} from 'lucide-react'
import Navbar from '../components/landing/Navbar'
import HeroSection from '../components/landing/HeroSection'
import Reveal from '../components/landing/Reveal'

const features = [
  {
    icon: FileText,
    title: 'RAG with real citations',
    desc: 'Documents are chunked, embedded and searched per bot, each in its own isolated collection. Every answer points back at the source chunk it came from — no silent hallucinations.',
  },
  {
    icon: Layers,
    title: 'Presets, then make it yours',
    desc: 'Six starting points — Support, Sales, Booking, Tutor, Coding, Character — or write your own system prompt and the bot becomes whatever you describe. The presets are a shortcut, not a menu.',
  },
  {
    icon: Wand2,
    title: 'AI prompt generator',
    desc: "Describe the bot in plain English and get a structured system prompt back. You don't have to be good at prompting to get a good bot.",
  },
  {
    icon: Workflow,
    title: 'Tool-using agent',
    desc: 'A real agent loop: the model picks tools — search the knowledge base, capture a lead, escalate — runs them, and iterates until it can answer.',
  },
  {
    icon: Zap,
    title: 'Token streaming',
    desc: 'Replies stream over Server-Sent Events, so answers appear as they are written instead of after an awkward pause. Works through any proxy.',
  },
  {
    icon: UserCheck,
    title: 'Confidence-gated handoff',
    desc: "The model rates its own certainty. Below the line — or on a complaint — the conversation escalates to a human instead of guessing.",
  },
  {
    icon: BarChart3,
    title: 'Analytics that act',
    desc: 'Top questions, channel breakdown, resolution rate — plus a knowledge-gap list telling you exactly which questions your docs fail to answer.',
  },
  {
    icon: Cpu,
    title: 'Not locked to one model',
    desc: 'Claude, OpenAI, or Together AI. One environment variable switches the whole platform — every call goes through a single client, so there are no code changes to make.',
  },
  {
    icon: ShieldCheck,
    title: 'Abuse protection built in',
    desc: 'Public chat endpoints are rate limited per visitor and capped per bot per day, so a stray script can never run up your model bill.',
  },
]

const steps = [
  { step: '01', title: 'Upload your knowledge', desc: 'Drag in PDFs, Word docs, spreadsheets or paste a URL. Everything is parsed, chunked, embedded and indexed automatically.' },
  { step: '02', title: 'Shape its personality', desc: 'Start from a preset, set the tone and rules, then customise as far as you want — up to writing the whole system prompt yourself, or describing it in a sentence and letting the generator draft it.' },
  { step: '03', title: 'Connect your channels', desc: 'Paste one script tag on your site, or connect WhatsApp, Instagram, Slack and Email with guided setup and a live credential test.' },
  { step: '04', title: 'Go live', desc: 'Flip the switch. Your bot answers with citations, escalates when unsure, and every conversation lands in your dashboard.' },
]

const channels = [
  { icon: Globe, name: 'Website widget', note: 'One script tag. Shadow DOM, so it never fights your CSS.' },
  { icon: MessageCircle, name: 'WhatsApp', note: 'Meta Cloud API, with your own number per bot.' },
  { icon: Instagram, name: 'Instagram', note: 'Auto-reply to DMs from a Business or Creator account.' },
  { icon: Slack, name: 'Slack', note: 'Answer questions right inside your workspace.' },
  { icon: Mail, name: 'Email', note: 'Send replies from your own support inbox over SMTP.' },
]

const openSourcePoints = [
  'MIT licensed — read, fork and audit every line',
  'Swap the language model with a single environment variable',
  'No per-seat pricing, no message caps, no vendor lock-in',
  'Multi-tenant from the start — every bot, document and conversation scoped to its own organisation',
]

export default function Landing() {
  return (
    <div className="bg-hero-bg min-h-screen">
      <Navbar />
      <HeroSection />

      {/* ── Features ─────────────────────────────────────────────────── */}
      <section id="features" className="relative bg-background px-6 md:px-10 lg:px-16 py-24 md:py-32 scroll-mt-20">
        <div className="max-w-7xl mx-auto">
          <Reveal>
            <span className="inline-flex items-center gap-2 text-xs uppercase tracking-widest text-primary mb-4">
              <Sparkles className="w-3.5 h-3.5" />
              Everything included
            </span>
            <h2 className="text-[clamp(2rem,4vw,3.25rem)] font-bold tracking-[-0.03em] leading-[1.1] text-foreground mb-4 uppercase">
              Built like a product,
              <br />
              <span className="text-primary">not a demo</span>
            </h2>
            <p className="text-muted-foreground text-base md:text-lg font-light max-w-2xl mb-14">
              Every piece below is implemented and working — retrieval, the agent loop, the
              channel integrations, the handoff logic. Not a roadmap.
            </p>
          </Reveal>

          <div className="grid sm:grid-cols-2 lg:grid-cols-3 gap-4">
            {features.map((feature, i) => (
              <Reveal key={feature.title} delay={(i % 3) * 0.08}>
                <div className="group h-full card-3d p-6">
                  <div className="icon-tile-soft w-11 h-11 mb-5 transition-transform duration-300 group-hover:scale-110">
                    <feature.icon className="w-5 h-5" />
                  </div>
                  <h3 className="text-lg font-semibold text-foreground mb-2">{feature.title}</h3>
                  <p className="text-muted-foreground text-sm font-light leading-relaxed">
                    {feature.desc}
                  </p>
                </div>
              </Reveal>
            ))}
          </div>
        </div>
      </section>

      {/* ── How it works ─────────────────────────────────────────────── */}
      <section id="how-it-works" className="relative bg-hero-bg px-6 md:px-10 lg:px-16 py-24 md:py-32 scroll-mt-20">
        <div className="max-w-5xl mx-auto">
          <Reveal>
            <span className="inline-flex items-center gap-2 text-xs uppercase tracking-widest text-primary mb-4">
              <Workflow className="w-3.5 h-3.5" />
              From zero to live
            </span>
            <h2 className="text-[clamp(2rem,4vw,3.25rem)] font-bold tracking-[-0.03em] leading-[1.1] text-foreground mb-14 uppercase">
              Four steps
            </h2>
          </Reveal>

          <div className="space-y-3">
            {steps.map((item, i) => (
              <Reveal key={item.step} delay={i * 0.08}>
                <div className="group flex gap-5 md:gap-8 items-start rounded-xl border border-border bg-card/60 p-5 md:p-7 transition-colors hover:border-primary/40">
                  <span className="flex-shrink-0 text-primary font-bold text-lg md:text-xl tabular-nums tracking-tight pt-0.5">
                    {item.step}
                  </span>
                  <div className="min-w-0">
                    <h3 className="text-base md:text-lg font-semibold text-foreground mb-1.5">
                      {item.title}
                    </h3>
                    <p className="text-muted-foreground text-sm font-light leading-relaxed">
                      {item.desc}
                    </p>
                  </div>
                </div>
              </Reveal>
            ))}
          </div>
        </div>
      </section>

      {/* ── Channels ─────────────────────────────────────────────────── */}
      <section id="channels" className="relative bg-background px-6 md:px-10 lg:px-16 py-24 md:py-32 scroll-mt-20">
        <div className="max-w-7xl mx-auto">
          <Reveal>
            <span className="inline-flex items-center gap-2 text-xs uppercase tracking-widest text-primary mb-4">
              <MessageSquare className="w-3.5 h-3.5" />
              Five channels
            </span>
            <h2 className="text-[clamp(2rem,4vw,3.25rem)] font-bold tracking-[-0.03em] leading-[1.1] text-foreground mb-4 uppercase">
              Wherever they<span className="text-primary"> message you</span>
            </h2>
            <p className="text-muted-foreground text-base md:text-lg font-light max-w-2xl mb-14">
              Each bot stores its own credentials, entered from the dashboard — so two bots can
              run two different numbers. A live test button calls the provider and reports the
              real error before you go live.
            </p>
          </Reveal>

          <div className="grid sm:grid-cols-2 lg:grid-cols-3 gap-4">
            {channels.map((channel, i) => (
              <Reveal key={channel.name} delay={(i % 3) * 0.08}>
                <div className="h-full flex items-start gap-4 rounded-xl border border-border bg-card p-5 transition-colors hover:border-primary/40">
                  <div className="icon-tile-soft w-10 h-10 flex-shrink-0">
                    <channel.icon className="w-4.5 h-4.5" />
                  </div>
                  <div className="min-w-0">
                    <h3 className="text-sm font-semibold text-foreground mb-1">{channel.name}</h3>
                    <p className="text-muted-foreground text-xs font-light leading-relaxed">
                      {channel.note}
                    </p>
                  </div>
                </div>
              </Reveal>
            ))}
          </div>
        </div>
      </section>

      {/* ── Open source ──────────────────────────────────────────────── */}
      <section id="open-source" className="relative bg-hero-bg px-6 md:px-10 lg:px-16 py-24 md:py-32 scroll-mt-20">
        <div className="max-w-6xl mx-auto grid lg:grid-cols-2 gap-12 lg:gap-16 items-center">
          <Reveal>
            <span className="inline-flex items-center gap-2 text-xs uppercase tracking-widest text-primary mb-4">
              <Github className="w-3.5 h-3.5" />
              MIT licensed
            </span>
            <h2 className="text-[clamp(2rem,4vw,3.25rem)] font-bold tracking-[-0.03em] leading-[1.1] text-foreground mb-6 uppercase">
              Yours to<span className="text-primary"> change</span>
            </h2>
            <p className="text-muted-foreground text-base md:text-lg font-light leading-relaxed mb-8">
              Retrieval happens inside the application itself — documents are embedded and
              searched without calling out to a paid embeddings API, so the only thing you pay
              for is the model that writes the final answer.
            </p>
            <ul className="space-y-3">
              {openSourcePoints.map((point) => (
                <li key={point} className="flex items-start gap-3 text-sm text-foreground/80 font-light">
                  <Check className="w-4 h-4 text-primary flex-shrink-0 mt-0.5" />
                  {point}
                </li>
              ))}
            </ul>
          </Reveal>

          {/* Show the actual output rather than describing it — a grounded,
              cited answer is the single clearest demonstration of what RAG buys you. */}
          <Reveal delay={0.12}>
            <div className="rounded-xl border border-border bg-card overflow-hidden shadow-depth-lg">
              <div className="flex items-center gap-2 px-4 py-3 border-b border-border bg-background/60">
                <span className="w-2 h-2 rounded-full bg-primary" />
                <span className="text-[11px] text-muted-foreground font-medium tracking-wide">
                  Support bot · website widget
                </span>
              </div>

              <div className="p-5 space-y-3">
                <div className="flex justify-end">
                  <p className="max-w-[85%] rounded-xl rounded-br-sm bg-primary px-3.5 py-2 text-[13px] text-primary-foreground">
                    Can I return something after 30 days?
                  </p>
                </div>

                <div className="flex justify-start">
                  <div className="max-w-[92%] rounded-xl rounded-bl-sm border border-border bg-background px-3.5 py-2.5">
                    <p className="text-[13px] leading-relaxed text-foreground/90">
                      Returns are accepted within 30 days of delivery, so a later request would
                      fall outside the standard window — but unopened items can still be
                      exchanged for store credit.
                    </p>
                    <div className="mt-2.5 flex flex-wrap items-center gap-2 border-t border-border pt-2">
                      <span className="inline-flex items-center gap-1 rounded-sm bg-primary/10 px-1.5 py-0.5 text-[10px] font-medium text-primary">
                        <FileText className="w-2.5 h-2.5" />
                        returns-policy.pdf
                      </span>
                      <span className="text-[10px] text-muted-foreground/70">confidence 8/10</span>
                    </div>
                  </div>
                </div>

                <p className="pt-1 text-[11px] leading-relaxed text-muted-foreground/60">
                  Every answer carries the document it came from. Drop below the confidence
                  threshold and the conversation escalates to a human instead of guessing.
                </p>
              </div>
            </div>
          </Reveal>
        </div>
      </section>

      {/* ── CTA ──────────────────────────────────────────────────────── */}
      <section className="relative bg-background px-6 md:px-10 lg:px-16 py-24 md:py-32 overflow-hidden">
        <div
          aria-hidden="true"
          className="pointer-events-none absolute inset-0 bg-gradient-brand-soft"
        />
        <div className="relative max-w-3xl mx-auto text-center">
          <Reveal>
            <h2 className="text-[clamp(2rem,5vw,3.75rem)] font-bold tracking-[-0.04em] leading-[1.05] text-foreground mb-5 uppercase">
              Ship a bot that<span className="text-primary"> knows things</span>
            </h2>
            <p className="text-muted-foreground text-base md:text-lg font-light mb-10 max-w-xl mx-auto">
              Free, open source, and running on your own machine in about five minutes.
            </p>
            <div className="flex flex-wrap items-center justify-center gap-3 font-bold">
              <Link
                to="/signup"
                className="inline-flex items-center gap-2 bg-primary text-primary-foreground px-8 py-4 text-sm rounded-sm hover:brightness-110 transition-all active:scale-[0.97]"
              >
                Start Building
                <ArrowRight className="w-4 h-4" />
              </Link>
              <Link
                to="/login"
                className="inline-flex items-center gap-2 bg-white text-background px-8 py-4 text-sm rounded-sm hover:brightness-90 transition-all active:scale-[0.97]"
              >
                <Bot className="w-4 h-4" />
                Explore the demo
              </Link>
            </div>
            <p className="text-muted-foreground/60 text-xs font-light mt-6">
              No credit card. No signup wall on the demo. MIT licensed.
            </p>
          </Reveal>
        </div>
      </section>

      {/* ── Footer ───────────────────────────────────────────────────── */}
      <footer className="bg-hero-bg border-t border-border px-6 md:px-10 lg:px-16 py-10">
        <div className="max-w-7xl mx-auto flex flex-col sm:flex-row items-center justify-between gap-4">
          <div className="flex items-center gap-2">
            <Code2 className="w-4 h-4 text-primary" />
            <span className="text-foreground text-sm font-semibold tracking-tight">LUMIO</span>
            <span className="text-muted-foreground/60 text-xs ml-2">&copy; 2026</span>
          </div>
          <span className="text-muted-foreground/60 text-xs">
            Built by Aniket Singh · MIT licensed
          </span>
        </div>
      </footer>
    </div>
  )
}
