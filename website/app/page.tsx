"use client"

import { Navigation } from "@/components/navigation"
import { Footer } from "@/components/footer"
import VideoSlider from "@/components/video-slider"
import { ArrowRight, Eye, Zap, Target, Code, Server, Smartphone, Volume2, MapPin, FileText, Shield, Wifi } from "lucide-react"
import Link from "next/link"
import Image from "next/image"

export default function Home() {
  return (
    <>
      <Navigation />
      <main>
        <section className="bg-gradient-to-br from-slate-900 via-slate-800 to-teal-900/20 py-12 md:py-20 relative overflow-hidden">
          <div className="absolute top-0 right-0 w-96 h-96 bg-teal-500/10 rounded-full blur-3xl -z-10" />

          <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-8 lg:gap-12 items-center">
              <div className="space-y-6">

                <div className="space-y-3">
                  <h1 className="text-4xl md:text-5xl lg:text-6xl font-bold text-balance leading-tight text-white">
                    IoT Smart Glasses with{" "}
                    <span className="bg-gradient-to-r from-teal-400 to-teal-300 bg-clip-text text-transparent">
                      TinyML & Edge AI
                    </span>
                  </h1>
                  <p className="text-lg md:text-xl text-slate-300 text-balance leading-relaxed">
                    Real-time assistance for visually impaired individuals in Sri Lanka through facial recognition, Sinhala voice navigation, and text reading—all powered by affordable, offline-capable technology.
                  </p>
                </div>
                <div className="flex flex-col sm:flex-row gap-4 pt-4">
                  <Link
                    href="/about"
                    className="inline-flex items-center justify-center gap-2 bg-gradient-to-r from-teal-500 to-teal-600 text-white px-8 py-3 rounded-lg font-semibold hover:shadow-lg hover:shadow-teal-500/50 transition-all duration-200 transform hover:scale-105"
                  >
                    Learn More <ArrowRight size={20} />
                  </Link>
                  <Link
                    href="/scope"
                    className="inline-flex items-center justify-center gap-2 border-2 border-teal-400 text-teal-400 px-8 py-3 rounded-lg font-semibold hover:bg-teal-400/10 transition-all duration-200"
                  >
                    Project Scope
                  </Link>
                </div>
              </div>

              <div className="h-96 md:h-[500px] rounded-2xl overflow-hidden shadow-2xl border border-teal-500/20">
                <VideoSlider />
              </div>
            </div>
          </div>
        </section>

        <section className="py-16 md:py-24 bg-white">
          <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
            <div className="text-center mb-12">
              <h2 className="text-3xl md:text-4xl font-bold mb-4 text-balance text-slate-900">
                Three Integrated Components
              </h2>
              <p className="text-slate-600 max-w-3xl mx-auto">
                A comprehensive assistive system combining facial recognition, voice navigation, and text reading—all designed specifically for the Sri Lankan visually impaired community
              </p>
            </div>
            <div className="grid grid-cols-1 md:grid-cols-3 gap-8">
              {[
                { 
                  icon: Eye, 
                  title: "Real-Time Facial Recognition", 
                  desc: "Identify known individuals with 92% accuracy. Dynamic enrollment via voice commands. Whisper feedback for privacy.",
                  tech: "FaceNet, MobileFaceNet, TensorFlow Lite"
                },
                { 
                  icon: MapPin, 
                  title: "Sinhala Voice Navigation", 
                  desc: "Speech-to-text commands (75-85% accuracy) with ultrasonic obstacle detection up to 1m. Real-time audio warnings.",
                  tech: "Whisper STT, HC-SR04 sensors, Android TTS"
                },
                {
                  icon: FileText,
                  title: "Sinhala Text Recognition",
                  desc: "OCR for printed Sinhala text with document classification (exam papers, newspapers, forms, notes, stories, words).",
                  tech: "Google ML Kit, Tesseract, CNN classification"
                },
              ].map((feature, idx) => {
                const Icon = feature.icon
                return (
                  <div
                    key={idx}
                    className="bg-gradient-to-br from-slate-50 to-white border border-slate-200 rounded-xl p-8 hover:shadow-xl hover:border-teal-300 transition-all duration-200 group"
                  >
                    <div className="w-16 h-16 rounded-full bg-gradient-to-br from-teal-500 to-teal-600 flex items-center justify-center mb-6 group-hover:scale-110 transition-transform">
                      <Icon className="w-8 h-8 text-white" />
                    </div>
                    <h3 className="font-semibold text-xl text-slate-900 mb-3">{feature.title}</h3>
                    <p className="text-slate-600 mb-4 leading-relaxed">{feature.desc}</p>
                    <div className="pt-4 border-t border-slate-100">
                      <p className="text-xs text-slate-500 font-medium">Technologies:</p>
                      <p className="text-xs text-teal-600 mt-1">{feature.tech}</p>
                    </div>
                  </div>
                )
              })}
            </div>
          </div>
        </section>

        <section className="py-16 md:py-24 bg-slate-50">
          <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
            <h2 className="text-3xl md:text-4xl font-bold text-center mb-4 text-balance text-slate-900">
              System Architecture
            </h2>
            <p className="text-center text-slate-600 mb-12 max-w-2xl mx-auto">
              Edge AI processing on Raspberry Pi 5 for privacy, affordability, and offline functionality
            </p>
            <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
              {[
                {
                  icon: Smartphone,
                  title: "Mobile Application",
                  desc: "Android/React Native app with voice commands, frame filtering, and Bluetooth communication",
                  features: ["Voice feedback system", "Accessibility features", "Sinhala & English support"]
                },
                {
                  icon: Server,
                  title: "Edge Server (Raspberry Pi 5)",
                  desc: "Flask REST API running as systemd service for local AI processing",
                  features: ["Face recognition", "Obstacle detection", "OCR processing"]
                },
                {
                  icon: Code,
                  title: "Smart Glasses Hardware",
                  desc: "Pi Camera Module 2 (8MP) mounted on lightweight frame with portable power",
                  features: ["Real-time capture", "Low latency", "Wearable design"]
                },
              ].map((item, idx) => {
                const Icon = item.icon
                return (
                  <div
                    key={idx}
                    className="rounded-xl overflow-hidden shadow-lg hover:shadow-xl transition-all duration-200 bg-white border border-slate-200 hover:border-teal-300"
                  >
                    <div className="h-48 bg-gradient-to-br from-teal-100 to-slate-100 flex items-center justify-center">
                      <Icon className="w-16 h-16 text-teal-500 opacity-50" />
                    </div>
                    <div className="p-6">
                      <h3 className="font-semibold text-lg text-slate-900 mb-2">{item.title}</h3>
                      <p className="text-slate-600 text-sm mb-4">{item.desc}</p>
                      <ul className="space-y-1">
                        {item.features.map((feature, fIdx) => (
                          <li key={fIdx} className="flex items-center gap-2 text-xs text-slate-600">
                            <span className="w-1 h-1 rounded-full bg-teal-500" />
                            {feature}
                          </li>
                        ))}
                      </ul>
                    </div>
                  </div>
                )
              })}
            </div>
          </div>
        </section>

        <section className="py-16 md:py-24 bg-white">
          <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
            <h2 className="text-3xl md:text-4xl font-bold text-center mb-4 text-balance text-slate-900">
              Hardware Components
            </h2>
            <p className="text-center text-slate-600 mb-12 max-w-2xl mx-auto">
              Affordable, accessible hardware totaling ~Rs. 70,000 (compared to OrCam's $3,500+)
            </p>
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
              {[
                { 
                  title: "Raspberry Pi 5", 
                  specs: ["Broadcom BCM2712", "8GB RAM, 8 TOPS", "2.4GHz Quad-core"],
                  cost: "~Rs. 43,000",
                  image: "/raspberry-pi-5-single-board-computer.jpg"
                },
                { 
                  title: "Pi Camera Module 2", 
                  specs: ["8MP Sony IMX219", "1080p video", "Wide-angle lens"],
                  cost: "~Rs. 6,500",
                  image: "/smart-glasses-hardware-with-camera-and-sensors.jpg"
                },
                {
                  title: "HC-SR04 Ultrasonic Sensors",
                  specs: ["2cm-1m range", "Real-time detection", "Multiple sensors"],
                  cost: "~Rs. 500 each",
                  image: "/ultrasonic-distance-sensor-hc-sr04.jpg"
                },
                {
                  title: "Power & Connectivity",
                  specs: ["27W USB-C supply", "Bluetooth/Wi-Fi", "Portable battery"],
                  cost: "~Rs. 10,000",
                  image: "/wifi-bluetooth-wireless-connectivity-module.jpg"
                },
              ].map((component, idx) => (
                <div
                  key={idx}
                  className="rounded-xl overflow-hidden shadow-lg hover:shadow-xl transition-all duration-200 bg-gradient-to-br from-slate-50 to-white border border-slate-200 hover:border-teal-300 group"
                >
                  <div className="relative h-40 w-full group-hover:opacity-90 transition-opacity">
                    <Image
                      src={component.image}
                      alt={component.title}
                      fill
                      className="object-cover"
                      sizes="(max-width: 768px) 100vw, (max-width: 1200px) 50vw, 25vw"
                    />
                  </div>
                  <div className="p-6">
                    <h3 className="font-semibold text-lg text-slate-900 mb-3">{component.title}</h3>
                    <ul className="text-xs text-slate-600 space-y-1 mb-3">
                      {component.specs.map((spec, specIdx) => (
                        <li key={specIdx} className="flex items-center gap-2">
                          <span className="w-1.5 h-1.5 rounded-full bg-teal-500" />
                          {spec}
                        </li>
                      ))}
                    </ul>
                    <div className="pt-3 border-t border-slate-100">
                      <p className="text-xs font-semibold text-teal-600">{component.cost}</p>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          </div>
        </section>

        <section className="py-16 md:py-24 bg-slate-50">
          <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
            <h2 className="text-3xl md:text-4xl font-bold text-center mb-4 text-balance text-slate-900">
              Why Our Solution Stands Out
            </h2>
            <p className="text-center text-slate-600 mb-12 max-w-2xl mx-auto">
              Designed specifically for the Sri Lankan context with privacy, affordability, and accessibility in mind
            </p>
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
              {[
                { 
                  icon: Shield, 
                  title: "Privacy First", 
                  desc: "100% on-device processing. No cloud dependency. Your data stays with you.",
                },
                { 
                  icon: Wifi, 
                  title: "Offline Capable", 
                  desc: "Works without internet. Perfect for rural areas with limited connectivity.",
                },
                {
                  icon: Volume2,
                  title: "Sinhala Support",
                  desc: "Native Sinhala speech recognition, TTS, and OCR—first of its kind.",
                },
                {
                  icon: Target,
                  title: "Affordable",
                  desc: "~Rs. 70,000 total cost—10x cheaper than commercial alternatives like OrCam.",
                },
              ].map((benefit, idx) => {
                const Icon = benefit.icon
                return (
                  <div
                    key={idx}
                    className="bg-white border border-slate-200 rounded-xl p-6 hover:shadow-lg hover:border-teal-300 transition-all duration-200 text-center"
                  >
                    <div className="w-12 h-12 rounded-full bg-teal-100 flex items-center justify-center mx-auto mb-4">
                      <Icon className="w-6 h-6 text-teal-600" />
                    </div>
                    <h3 className="font-semibold text-lg text-slate-900 mb-2">{benefit.title}</h3>
                    <p className="text-slate-600 text-sm leading-relaxed">{benefit.desc}</p>
                  </div>
                )
              })}
            </div>
          </div>
        </section>

        <section className="py-16 md:py-24 bg-white">
          <div className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8 text-center">
            <h2 className="text-3xl md:text-4xl font-bold mb-6 text-slate-900">
              Research Impact
            </h2>
            <p className="text-lg text-slate-600 leading-relaxed mb-8">
              This research advances intelligent, real-time assistance systems by demonstrating that IoT Smart Glasses can operate efficiently in low-power, privacy-sensitive environments while maintaining high accuracy and reliability for visually impaired individuals in developing regions.
            </p>
            <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-8">
              {[
                { label: "Recognition Accuracy", value: "92%", detail: "Controlled conditions" },
                { label: "Response Latency", value: "<1s", detail: "Real-time performance" },
                { label: "Cost Reduction", value: "10x", detail: "vs. commercial solutions" },
              ].map((metric, idx) => (
                <div key={idx} className="bg-gradient-to-br from-teal-50 to-slate-50 border border-teal-200 rounded-xl p-6">
                  <div className="text-4xl font-bold text-teal-600 mb-2">{metric.value}</div>
                  <div className="font-semibold text-slate-900 mb-1">{metric.label}</div>
                  <div className="text-sm text-slate-600">{metric.detail}</div>
                </div>
              ))}
            </div>
          </div>
        </section>

        <section className="bg-gradient-to-r from-slate-900 via-teal-900 to-slate-900 text-white py-16 md:py-24 relative overflow-hidden">
          <div className="absolute top-0 left-0 w-96 h-96 bg-teal-500/10 rounded-full blur-3xl -z-10" />

          <div className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8 text-center space-y-6">
            <h2 className="text-3xl md:text-4xl font-bold text-balance">Empowering Independence Through Technology</h2>
            <p className="text-lg text-slate-300 text-balance max-w-2xl mx-auto">
              Explore our comprehensive research project and discover how edge AI and TinyML are revolutionizing assistive technology for visually impaired individuals in Sri Lanka.
            </p>
            <div className="flex flex-col sm:flex-row gap-4 justify-center pt-4">
              <Link
                href="/team"
                className="inline-flex items-center justify-center gap-2 bg-teal-500 text-white px-8 py-3 rounded-lg font-semibold hover:bg-teal-600 transition-all duration-200 transform hover:scale-105"
              >
                Meet Our Team <ArrowRight size={20} />
              </Link>
              <Link
                href="/documentation"
                className="inline-flex items-center justify-center gap-2 border-2 border-teal-400 text-teal-400 px-8 py-3 rounded-lg font-semibold hover:bg-teal-400/10 transition-all duration-200"
              >
                View Documentation
              </Link>
            </div>
          </div>
        </section>
      </main>
      <Footer />
    </>
  )
}