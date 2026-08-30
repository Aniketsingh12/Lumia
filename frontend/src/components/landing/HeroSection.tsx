import { Component, lazy, Suspense, type ReactNode } from 'react'
import { Link } from 'react-router-dom'

// Code-split: the Spline runtime is large, and nothing above the fold depends
// on it, so it must not sit in the main bundle.
const Spline = lazy(() => import('@splinetool/react-spline'))

const SPLINE_SCENE = 'https://prod.spline.design/Slk6b8kz3LRlKiyk/scene.splinecode'

/**
 * The scene is fetched from a third-party CDN at runtime. Suspense covers the
 * loading window but not a *failed* load — without this boundary, an outage,
 * a blocked request, or a WebGL-less browser would throw during render and take
 * the entire landing page down with it. Falling back to the flat hero
 * background keeps the copy and CTAs perfectly usable.
 */
class SplineBoundary extends Component<{ children: ReactNode; fallback: ReactNode }, { failed: boolean }> {
  state = { failed: false }

  static getDerivedStateFromError() {
    return { failed: true }
  }

  render() {
    return this.state.failed ? this.props.fallback : this.props.children
  }
}

export default function HeroSection() {
  const sceneFallback = <div className="absolute inset-0 bg-hero-bg" />

  return (
    <section className="relative min-h-screen flex items-end bg-hero-bg overflow-hidden">
      {/* 3D background */}
      <div className="absolute inset-0">
        <SplineBoundary fallback={sceneFallback}>
          <Suspense fallback={sceneFallback}>
            <Spline scene={SPLINE_SCENE} className="w-full h-full" />
          </Suspense>
        </SplineBoundary>
      </div>

      {/* Darkening wash so the copy stays legible over the animated scene */}
      <div className="absolute inset-0 bg-black/30 z-[1] pointer-events-none" />

      {/* Content is click-through so the Spline scene stays interactive;
          individual controls re-enable pointer events for themselves. */}
      <div className="relative z-10 pointer-events-none w-full max-w-[90%] sm:max-w-md lg:max-w-2xl px-6 md:px-10 pb-10 md:pb-10 pt-32">
        <h1
          className="opacity-0 animate-fade-up text-[clamp(3rem,8vw,6rem)] font-bold leading-[1.05] tracking-[-0.05em] text-foreground mb-2 md:mb-4 uppercase"
          style={{ animationDelay: '0.2s' }}
        >
          Lumio<span className="text-primary"> AI</span>
        </h1>

        <p
          className="opacity-0 animate-fade-up text-foreground/80 text-[clamp(1.125rem,2.5vw,1.875rem)] font-light mb-3 md:mb-6"
          style={{ animationDelay: '0.4s' }}
        >
          Chatbots that actually know your business.
        </p>

        <p
          className="opacity-0 animate-fade-up text-muted-foreground text-[clamp(0.875rem,1.5vw,1.25rem)] font-light mb-4 md:mb-8"
          style={{ animationDelay: '0.55s' }}
        >
          Upload your documents and get a bot that answers from them — citing its sources,
          scoring its own confidence, and handing off to a human the moment it isn't sure.
          Live on your website, WhatsApp, Instagram and Slack in an afternoon.
        </p>

        <div
          className="opacity-0 animate-fade-up flex flex-wrap gap-3 font-bold"
          style={{ animationDelay: '0.7s' }}
        >
          <Link
            to="/signup"
            className="pointer-events-auto bg-primary text-primary-foreground px-6 py-3 md:px-8 md:py-4 text-sm rounded-sm cursor-pointer hover:brightness-110 transition-all active:scale-[0.97]"
          >
            Start Building
          </Link>
          <a
            href="#features"
            className="pointer-events-auto bg-white text-background px-6 py-3 md:px-8 md:py-4 text-sm rounded-sm cursor-pointer hover:brightness-90 transition-all active:scale-[0.97]"
          >
            See Features
          </a>
        </div>

        <p
          className="opacity-0 animate-fade-up text-muted-foreground/60 text-xs font-light mt-4 md:mt-6"
          style={{ animationDelay: '0.85s' }}
        >
          Open source · MIT licensed · Five channels · Bring your own model.
        </p>
      </div>
    </section>
  )
}
