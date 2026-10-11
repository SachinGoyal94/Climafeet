import { useEffect, useRef } from 'react'

export default function LandingHero() {
  const videoRef = useRef<HTMLVideoElement>(null)

  useEffect(() => {
    const video = videoRef.current
    if (!video) return

    const reducedMotion = window.matchMedia('(prefers-reduced-motion: reduce)')
    let isVisible = false

    const syncPlayback = () => {
      if (isVisible && !document.hidden && !reducedMotion.matches) {
        void video.play().catch(() => {})
      } else {
        video.pause()
      }
    }

    const observer = new IntersectionObserver(
      ([entry]) => {
        isVisible = entry.isIntersecting
        syncPlayback()
      },
      { threshold: 0.15 },
    )

    observer.observe(video)
    document.addEventListener('visibilitychange', syncPlayback)
    reducedMotion.addEventListener('change', syncPlayback)

    return () => {
      observer.disconnect()
      document.removeEventListener('visibilitychange', syncPlayback)
      reducedMotion.removeEventListener('change', syncPlayback)
      video.pause()
    }
  }, [])

  return (
    <section className="hero" aria-labelledby="hero-title">
      <video
        ref={videoRef}
        className="hero-video"
        muted
        loop
        playsInline
        preload="metadata"
        aria-hidden="true"
        tabIndex={-1}
      >
        <source src="/truck-driving.mp4" type="video/mp4" />
      </video>
      <div className="hero-overlay" aria-hidden="true" />

      <div className="hero-shell">
        <nav className="topbar" aria-label="Main navigation">
          <a className="brand" href="#top" aria-label="Climafeet home">
            <span className="brand-symbol" aria-hidden="true">
              <svg viewBox="0 0 36 36" fill="none">
                <path d="M7 25.5 13.5 19l5 5L29 13.5" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round" />
                <path d="M22 13.5h7v7" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round" />
                <circle cx="7" cy="25.5" r="2.5" fill="currentColor" />
              </svg>
            </span>
            <span className="brand-copy">
              <strong>clima<span>feet</span></strong>
              <small>WEATHER-AWARE ROUTING</small>
            </span>
          </a>

          <div className="topbar-links">
            <a href="#planner">Planner</a>
            <a href="#approach">How it works</a>
          </div>

          <a className="topbar-cta" href="#planner">
            Open planner <span aria-hidden="true">↗</span>
          </a>
        </nav>

        <div className="hero-copy">
          <p className="hero-kicker"><i aria-hidden="true" /> WEATHER-AWARE DISPATCH</p>
          <h1 id="hero-title">Make every mile <span>weather-aware.</span></h1>
          <p className="hero-description">
            Plan truck routes around the conditions your load will meet—at the time it gets there.
          </p>
          <div className="hero-actions">
            <a className="button-light" href="#planner">
              Plan a route <span aria-hidden="true">↗</span>
            </a>
            <a className="button-quiet" href="#approach">Explore the approach <span aria-hidden="true">↓</span></a>
          </div>
        </div>

        <div className="hero-bottom">
          <div className="hero-stats" aria-label="Climafeet features">
            <div className="hero-stat">
              <strong>Up to <b>3</b></strong>
              <span>truck routes compared</span>
            </div>
            <div className="hero-stat">
              <strong><b>48</b> hours</strong>
              <span>corridor forecast</span>
            </div>
            <div className="hero-stat">
              <strong><b>10 / 25 / 50</b> mi</strong>
              <span>checkpoint spacing</span>
            </div>
          </div>
          <a className="scroll-cue" href="#planner">
            <span>SCROLL TO PLAN</span><i aria-hidden="true">↓</i>
          </a>
        </div>
      </div>
    </section>
  )
}
