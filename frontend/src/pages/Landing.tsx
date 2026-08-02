import { Link } from 'react-router-dom'
import {
  Sparkles, Zap, MessageSquare, BarChart3, Globe, Shield, Bot,
  ArrowRight, Check,
} from 'lucide-react'

const features = [
  { icon: Bot, title: 'AI-Powered RAG', desc: 'Answers come from your own documents, with source citations and a confidence score on every reply.' },
  { icon: MessageSquare, title: 'Multi-Channel', desc: 'Website widget, WhatsApp, Instagram, Slack and Email — connected from the dashboard, no config files.' },
  { icon: Zap, title: 'Six Bot Genres', desc: 'Support, Sales, Booking, Tutor, Coding, or a custom character persona for casual conversation.' },
  { icon: BarChart3, title: 'Smart Analytics', desc: 'Top questions, knowledge gaps, channel breakdown and satisfaction — all at a glance.' },
  { icon: Globe, title: 'Human Handoff', desc: 'The AI handles routine queries and escalates anything it is not confident about to a real agent.' },
  { icon: Shield, title: 'Self-Hosted', desc: 'Run it on your own infrastructure with local models. Your data never leaves your servers.' },
]

const steps = [
  { step: '1', title: 'Upload Your Knowledge', desc: 'Drag in PDFs, docs or URLs. We chunk, embed and index everything automatically.' },
  { step: '2', title: 'Pick a Genre & Personality', desc: 'Choose what kind of bot it is, set the tone and rules — or let the AI write the prompt for you.' },
  { step: '3', title: 'Connect Your Channels', desc: 'Paste one script tag on your site, or connect WhatsApp, Instagram and Slack with a guided setup.' },
  { step: '4', title: 'Go Live', desc: 'Flip the switch. Your bot starts answering with citations, and escalates when it is unsure.' },
]

export default function Landing() {
  return (
    <div className="min-h-screen relative overflow-x-hidden">
      {/* Ambient background */}
      <div className="app-mesh" />
      {/* Floating orbs for depth — decorative only */}
      <div
        aria-hidden="true"
        className="pointer-events-none fixed -top-40 -left-40 w-[32rem] h-[32rem] rounded-full bg-primary-400/20 blur-3xl animate-float-slow"
      />
      <div
        aria-hidden="true"
        className="pointer-events-none fixed top-1/3 -right-40 w-[28rem] h-[28rem] rounded-full bg-accent-400/20 blur-3xl animate-float-slow"
        style={{ animationDelay: '3s' }}
      />

      {/* Nav */}
      <nav className="sticky top-0 z-30 backdrop-blur-xl bg-white/60 border-b border-white/60">
        <div className="flex items-center justify-between px-4 sm:px-6 py-3 max-w-7xl mx-auto">
          <div className="flex items-center gap-2.5">
            <div className="icon-tile w-9 h-9">
              <Sparkles className="w-5 h-5" />
            </div>
            <span className="text-xl font-bold tracking-tight text-ink-900">Lumio</span>
          </div>
          <div className="flex items-center gap-2 sm:gap-4">
            <Link
              to="/login"
              className="text-ink-600 hover:text-ink-900 font-semibold text-sm px-3 py-2 transition-colors"
            >
              Log in
            </Link>
            <Link to="/signup" className="btn-primary">
              <span className="hidden sm:inline">Get Started Free</span>
              <span className="sm:hidden">Sign up</span>
            </Link>
          </div>
        </div>
      </nav>

      {/* Hero */}
      <section className="px-4 sm:px-6 pt-16 sm:pt-24 pb-20 sm:pb-28 max-w-7xl mx-auto text-center">
        <div className="inline-flex items-center gap-2 px-4 py-2 rounded-full text-primary-700 text-xs sm:text-sm font-semibold mb-8 bg-white/70 backdrop-blur border border-primary-200/60 shadow-depth-sm">
          <Zap className="w-4 h-4" />
          Open-source AI chatbot platform
        </div>

        <h1 className="text-4xl sm:text-6xl lg:text-7xl font-extrabold text-ink-900 leading-[1.05] tracking-tight mb-6">
          Build AI chatbots
          <br />
          <span className="text-gradient">in five minutes</span>
        </h1>

        <p className="text-base sm:text-xl text-ink-600 max-w-2xl mx-auto mb-10 leading-relaxed">
          Upload your documents, pick a personality, and deploy an intelligent chatbot across
          your website, WhatsApp, Instagram and Slack. No code required.
        </p>

        <div className="flex flex-col sm:flex-row items-center justify-center gap-3 sm:gap-4">
          <Link to="/signup" className="btn-primary w-full sm:w-auto !text-base !px-7 !py-3.5">
            Start building — it's free
            <ArrowRight className="w-4 h-4" />
          </Link>
          <a href="#features" className="btn-secondary w-full sm:w-auto !text-base !px-7 !py-3.5">
            See how it works
          </a>
        </div>

        {/* 3D dashboard mockup — tilted in perspective, straightens on hover */}
        <div className="mt-16 sm:mt-20 [perspective:2000px]">
          <div
            className="mx-auto max-w-5xl rounded-2xl overflow-hidden border border-white/70 bg-white/80 backdrop-blur-xl shadow-depth-xl
                       transition-transform duration-700 ease-out
                       [transform:rotateX(12deg)] hover:[transform:rotateX(0deg)]"
          >
            <div className="flex items-center gap-2 px-4 py-3 bg-ink-100/80 border-b border-ink-200">
              <div className="w-3 h-3 rounded-full bg-red-400" />
              <div className="w-3 h-3 rounded-full bg-yellow-400" />
              <div className="w-3 h-3 rounded-full bg-green-400" />
              <span className="text-xs sm:text-sm text-ink-500 ml-2 truncate">lumio.app/dashboard</span>
            </div>
            <div className="p-6 sm:p-10 bg-gradient-to-br from-primary-50/60 via-white to-accent-50/60 min-h-[240px] sm:min-h-[320px]">
              {/* Mini stat row */}
              <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 mb-6">
                {[
                  { label: 'Total Bots', value: '6' },
                  { label: 'Active', value: '4' },
                  { label: 'Messages', value: '12.4k' },
                  { label: 'Resolved', value: '87%' },
                ].map((s) => (
                  <div key={s.label} className="card p-3 text-left">
                    <p className="text-[11px] text-ink-500">{s.label}</p>
                    <p className="text-lg sm:text-xl font-bold text-ink-900">{s.value}</p>
                  </div>
                ))}
              </div>
              {/* Mini chat preview */}
              <div className="card p-4 text-left max-w-md mx-auto space-y-2.5">
                <div className="flex justify-end">
                  <span className="px-3 py-2 rounded-2xl rounded-br-sm bg-gradient-to-br from-primary-500 to-primary-700 text-white text-xs shadow-glow">
                    What are your opening hours?
                  </span>
                </div>
                <div className="flex justify-start">
                  <span className="px-3 py-2 rounded-2xl rounded-bl-sm bg-white border border-ink-200 text-ink-700 text-xs shadow-depth-sm">
                    We're open 9–6, Mon to Fri. <span className="text-primary-600">[Source 1]</span>
                  </span>
                </div>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* Features */}
      <section id="features" className="px-4 sm:px-6 py-20 sm:py-24 scroll-mt-20">
        <div className="max-w-7xl mx-auto">
          <h2 className="text-3xl sm:text-4xl font-bold text-center text-ink-900 mb-4 tracking-tight">
            Everything you need
          </h2>
          <p className="text-ink-600 text-center mb-14 max-w-2xl mx-auto">
            A complete platform to build, deploy and manage AI chatbots that actually help
            your customers.
          </p>
          <div className="grid sm:grid-cols-2 lg:grid-cols-3 gap-5">
            {features.map((feature) => (
              <div key={feature.title} className="card-3d p-6 group">
                <div className="icon-tile w-12 h-12 mb-4 transition-transform duration-300 group-hover:scale-110 group-hover:rotate-3">
                  <feature.icon className="w-6 h-6" />
                </div>
                <h3 className="text-lg font-bold text-ink-900 mb-2">{feature.title}</h3>
                <p className="text-ink-600 text-sm leading-relaxed">{feature.desc}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* How It Works */}
      <section className="px-4 sm:px-6 py-20 sm:py-24">
        <div className="max-w-4xl mx-auto">
          <h2 className="text-3xl sm:text-4xl font-bold text-center text-ink-900 mb-14 tracking-tight">
            How it works
          </h2>
          <div className="space-y-5">
            {steps.map((item) => (
              <div key={item.step} className="card-3d p-5 sm:p-6 flex gap-4 sm:gap-6 items-start">
                <div className="flex-shrink-0 w-11 h-11 sm:w-12 sm:h-12 rounded-2xl bg-gradient-to-br from-primary-500 to-accent-500 text-white flex items-center justify-center font-bold text-lg shadow-glow">
                  {item.step}
                </div>
                <div className="min-w-0">
                  <h3 className="text-base sm:text-lg font-bold text-ink-900 mb-1.5">
                    {item.title}
                  </h3>
                  <p className="text-ink-600 text-sm leading-relaxed">{item.desc}</p>
                </div>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* CTA */}
      <section className="px-4 sm:px-6 py-16 sm:py-20">
        <div className="max-w-4xl mx-auto rounded-3xl bg-gradient-to-br from-primary-600 via-primary-700 to-accent-600 px-6 sm:px-12 py-14 text-center shadow-glow-lg relative overflow-hidden">
          {/* Sheen overlay */}
          <div
            aria-hidden="true"
            className="absolute inset-0 bg-gradient-to-b from-white/20 to-transparent pointer-events-none"
          />
          <div className="relative">
            <h2 className="text-2xl sm:text-4xl font-bold text-white mb-4 tracking-tight">
              Ready to build your AI chatbot?
            </h2>
            <p className="text-primary-100 text-base sm:text-lg mb-8 max-w-xl mx-auto">
              Free and open source. Run it locally with Ollama, or deploy it in minutes.
            </p>
            <div className="flex flex-col sm:flex-row items-center justify-center gap-3">
              <Link
                to="/signup"
                className="w-full sm:w-auto inline-flex items-center justify-center gap-2 bg-white text-primary-700 px-7 py-3.5 rounded-xl font-bold shadow-depth-lg hover:-translate-y-0.5 hover:shadow-depth-xl transition-all duration-200"
              >
                Get started free
                <ArrowRight className="w-4 h-4" />
              </Link>
            </div>
            <div className="flex flex-wrap items-center justify-center gap-x-6 gap-y-2 mt-8 text-primary-100 text-sm">
              {['No credit card', 'Open source', 'Runs offline'].map((t) => (
                <span key={t} className="inline-flex items-center gap-1.5">
                  <Check className="w-4 h-4" />
                  {t}
                </span>
              ))}
            </div>
          </div>
        </div>
      </section>

      {/* Footer */}
      <footer className="px-4 sm:px-6 py-8 border-t border-white/60 backdrop-blur-sm">
        <div className="max-w-7xl mx-auto flex flex-col sm:flex-row items-center justify-between gap-3">
          <div className="flex items-center gap-2">
            <Sparkles className="w-5 h-5 text-primary-500" />
            <span className="text-ink-500 text-sm">Lumio &copy; 2026</span>
          </div>
          <span className="text-ink-500 text-sm">Built by Aniket Singh</span>
        </div>
      </footer>
    </div>
  )
}
