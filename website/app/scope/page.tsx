import { Navigation } from "@/components/navigation"
import { Footer } from "@/components/footer"
import { VideoHero } from "@/components/video-hero"
import { Target, Users, Zap, BookOpen, Server, Smartphone, Eye, MapPin, FileText } from "lucide-react"

export default function Scope() {
  return (
    <>
      <Navigation />
      <main>
        <VideoHero />

        <section className="py-16 md:py-24 bg-white">
          <div className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8">
            <h2 className="text-3xl font-bold mb-8 flex items-center gap-3 text-slate-900">
              <Target className="w-8 h-8 text-teal-500" />
              Project Objectives
            </h2>
            <div className="space-y-4">
              {[
                {
                  title: "Main Objective",
                  desc: "To design and implement an integrated IoT Smart Glasses system with TinyML and Edge AI that provides real-time assistance for visually impaired individuals in Sri Lanka through facial recognition, navigation support, and Sinhala text reading capabilities.",
                },
                {
                  title: "Specific Objectives",
                  items: [
                    "Develop real-time facial recognition system for identifying known individuals with personalized voice feedback",
                    "Implement Sinhala speech-to-text and text-to-speech navigation aid with ultrasonic obstacle detection",
                    "Create Sinhala text recognition (OCR) with voice feedback for reading printed materials",
                    "Deploy lightweight AI models on resource-constrained devices (Raspberry Pi 5)",
                    "Ensure offline functionality without cloud dependency for privacy and accessibility",
                    "Provide affordable solution (~Rs. 70,000) compared to commercial alternatives",
                  ],
                },
              ].map((obj, idx) => (
                <div
                  key={idx}
                  className="bg-gradient-to-br from-slate-50 to-white border border-slate-200 rounded-xl p-6 hover:border-teal-300 transition-colors"
                >
                  <h3 className="font-semibold text-lg text-slate-900 mb-2">{obj.title}</h3>
                  {obj.desc && <p className="text-slate-600">{obj.desc}</p>}
                  {obj.items && (
                    <ul className="space-y-2 text-slate-600">
                      {obj.items.map((item, itemIdx) => (
                        <li key={itemIdx} className="flex items-start gap-2">
                          <span className="w-1.5 h-1.5 rounded-full bg-teal-500 mt-2 flex-shrink-0" />
                          <span>{item}</span>
                        </li>
                      ))}
                    </ul>
                  )}
                </div>
              ))}
            </div>
          </div>
        </section>

        <section className="py-16 md:py-24 bg-slate-50">
          <div className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8">
            <h2 className="text-3xl font-bold mb-8 text-slate-900">System Architecture</h2>
            <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-8">
              {[
                {
                  icon: Smartphone,
                  title: "Mobile Application",
                  desc: "Android/React Native app with voice commands, frame filtering, and audio feedback",
                },
                { 
                  icon: Server, 
                  title: "Edge Server", 
                  desc: "Raspberry Pi 5 running Flask services for local AI processing" 
                },
                { 
                  icon: Zap, 
                  title: "Smart Glasses", 
                  desc: "Pi Camera Module 2 mounted on lightweight frame with portable power" 
                },
              ].map((item, idx) => {
                const Icon = item.icon
                return (
                  <div
                    key={idx}
                    className="bg-white border border-slate-200 rounded-xl overflow-hidden hover:shadow-lg transition-shadow"
                  >
                    <div className="h-40 bg-gradient-to-br from-teal-100 to-slate-100 flex items-center justify-center">
                      <Icon className="w-12 h-12 text-teal-500 opacity-50" />
                    </div>
                    <div className="p-4">
                      <h3 className="font-semibold text-slate-900 mb-1">{item.title}</h3>
                      <p className="text-slate-600 text-sm">{item.desc}</p>
                    </div>
                  </div>
                )
              })}
            </div>

            <div className="bg-gradient-to-r from-teal-50 to-slate-50 border border-teal-200 rounded-xl p-6">
              <h3 className="font-semibold text-lg text-slate-900 mb-4">Flask Server Services & Functions</h3>
              <div className="grid grid-cols-1 md:grid-cols-3 gap-4 text-sm">
                {[
                  { port: "Face Recognition", desc: "FaceNet/MobileFaceNet models with TensorFlow Lite for identifying known individuals" },
                  { port: "Navigation System", desc: "HC-SR04 ultrasonic sensors for obstacle detection up to 1m range" },
                  { port: "OCR Service", desc: "Sinhala text recognition with Google ML Kit/Tesseract and TTS synthesis" },
                ].map((service, idx) => (
                  <div key={idx}>
                    <p className="font-medium text-teal-600 mb-2">{service.port}</p>
                    <p className="text-slate-600">{service.desc}</p>
                  </div>
                ))}
              </div>
            </div>
          </div>
        </section>

        <section className="py-16 md:py-24 bg-white">
          <div className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8">
            <h2 className="text-3xl font-bold mb-8 flex items-center gap-3 text-slate-900">
              <Users className="w-8 h-8 text-teal-500" />
              Target Users
            </h2>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
              {[
                {
                  title: "Primary Users",
                  items: [
                    "Visually impaired individuals in Sri Lanka (285M+ globally with visual impairment)",
                    "Blind users seeking independence in navigation and social interaction",
                    "Sinhala-speaking community requiring localized assistive technology",
                    "Users in rural areas with limited internet connectivity",
                  ],
                },
                {
                  title: "Key Needs Addressed",
                  items: [
                    "Recognizing familiar people in social environments",
                    "Safe navigation with real-time obstacle detection",
                    "Reading printed Sinhala text independently",
                    "Affordable alternative to expensive commercial solutions (OrCam $3,500+)",
                  ],
                },
              ].map((userGroup, idx) => (
                <div
                  key={idx}
                  className="bg-gradient-to-br from-slate-50 to-white border border-slate-200 rounded-xl p-6 hover:border-teal-300 transition-colors"
                >
                  <h3 className="font-semibold text-lg text-slate-900 mb-3">{userGroup.title}</h3>
                  <ul className="space-y-2 text-slate-600 text-sm">
                    {userGroup.items.map((item, itemIdx) => (
                      <li key={itemIdx} className="flex items-start gap-2">
                        <span className="w-1.5 h-1.5 rounded-full bg-teal-500 mt-2 flex-shrink-0" />
                        <span>{item}</span>
                      </li>
                    ))}
                  </ul>
                </div>
              ))}
            </div>
          </div>
        </section>

        <section className="py-16 md:py-24 bg-slate-50">
          <div className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8">
            <h2 className="text-3xl font-bold mb-8 flex items-center gap-3 text-slate-900">
              <Zap className="w-8 h-8 text-teal-500" />
              Technical Specifications
            </h2>
            <div className="space-y-6">
              {[
                {
                  title: "Hardware Components",
                  specs: [
                    { label: "Processor", value: "Raspberry Pi 5 (Broadcom BCM2712, 8GB RAM)" },
                    { label: "Camera", value: "Pi Camera Module 2 (8MP Sony IMX219)" },
                    { label: "Power", value: "27W USB-C Power Supply + Portable battery" },
                    { label: "Total Cost", value: "~Rs. 70,000 ($200 USD)" },
                  ],
                },
                {
                  title: "Software & AI Models",
                  items: [
                    "TensorFlow Lite for edge AI optimization (float16 quantization)",
                    "Face recognition: 92% accuracy (controlled), 85% (real-world)",
                    "Sinhala OCR: 68% accuracy (controlled), 50% (real-world)",
                    "Speech recognition: 75-85% accuracy for Sinhala commands",
                    "Inference time: <1 second for face recognition",
                    "Offline operation: No internet required for core functionality",
                  ],
                },
              ].map((spec, idx) => (
                <div
                  key={idx}
                  className="bg-white border border-slate-200 rounded-xl p-6 hover:border-teal-300 transition-colors"
                >
                  <h3 className="font-semibold text-lg text-slate-900 mb-4">{spec.title}</h3>
                  {spec.specs && (
                    <div className="grid grid-cols-1 md:grid-cols-2 gap-4 text-sm text-slate-600">
                      {spec.specs.map((s, sIdx) => (
                        <div key={sIdx}>
                          <p className="font-medium text-slate-900 mb-1">{s.label}</p>
                          <p>{s.value}</p>
                        </div>
                      ))}
                    </div>
                  )}
                  {spec.items && (
                    <ul className="space-y-2 text-slate-600 text-sm">
                      {spec.items.map((item, itemIdx) => (
                        <li key={itemIdx} className="flex items-start gap-2">
                          <span className="w-1.5 h-1.5 rounded-full bg-teal-500 mt-2 flex-shrink-0" />
                          <span>{item}</span>
                        </li>
                      ))}
                    </ul>
                  )}
                </div>
              ))}
            </div>
          </div>
        </section>

        <section className="py-16 md:py-24 bg-white">
          <div className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8">
            <h2 className="text-3xl font-bold mb-8 flex items-center gap-3 text-slate-900">
              <BookOpen className="w-8 h-8 text-teal-500" />
              System Components
            </h2>
            <div className="space-y-4">
              {[
                { 
                  icon: Eye,
                  name: "Facial Recognition Module", 
                  desc: "Real-time identification of known individuals using pretrained FaceNet model, with dynamic user enrollment via mobile app and voice commands. Provides whisper feedback for privacy." 
                },
                { 
                  icon: MapPin,
                  name: "Navigation System", 
                  desc: "Sinhala speech-to-text commands with ultrasonic obstacle detection (HC-SR04 sensor, 2cm-1m range). Real-time audio warnings and voice-guided assistance." 
                },
                { 
                  icon: FileText,
                  name: "OCR & Document Recognition", 
                  desc: "Sinhala text recognition with 78% document classification accuracy (exam papers, newspapers, forms, notes, stories, word docs). TTS conversion for audio feedback." 
                },
                { 
                  icon: Smartphone,
                  name: "Mobile Application", 
                  desc: "Android app for frame filtering, user interaction, and system configuration. Supports voice commands in Sinhala and English with accessibility features." 
                },
                { 
                  icon: Server,
                  name: "Edge Processing", 
                  desc: "Local Flask server on Raspberry Pi 5 running as systemd service. All AI processing happens on-device for privacy and offline functionality." 
                },
                { 
                  icon: Zap,
                  name: "TinyML Optimization", 
                  desc: "Models compressed using TensorFlow Lite with quantization. Low latency (<1s), minimal power consumption, suitable for wearable devices." 
                },
              ].map((component, idx) => {
                const Icon = component.icon
                return (
                  <div
                    key={idx}
                    className="bg-gradient-to-r from-slate-50 to-white border border-slate-200 rounded-xl p-4 flex items-start gap-4 hover:border-teal-300 transition-colors"
                  >
                    <div className="w-10 h-10 rounded-full bg-gradient-to-br from-teal-500 to-teal-600 text-white flex items-center justify-center flex-shrink-0">
                      <Icon className="w-5 h-5" />
                    </div>
                    <div>
                      <h3 className="font-semibold text-slate-900">{component.name}</h3>
                      <p className="text-slate-600 text-sm mt-1">{component.desc}</p>
                    </div>
                  </div>
                )
              })}
            </div>
          </div>
        </section>

        <section className="py-16 md:py-24 bg-slate-50">
          <div className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8">
            <h2 className="text-3xl font-bold mb-8 text-slate-900">Research Contributions</h2>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
              {[
                {
                  title: "Technical Innovation",
                  items: [
                    "First integrated system combining face recognition, navigation, and OCR for Sinhala",
                    "Edge AI deployment on low-cost hardware (Raspberry Pi 5)",
                    "Offline functionality preserving user privacy",
                    "Real-time performance suitable for daily use",
                  ],
                },
                {
                  title: "Social Impact",
                  items: [
                    "Affordable solution (10x cheaper than OrCam MyEye)",
                    "Localized for Sri Lankan visually impaired community",
                    "Enhanced independence and social confidence",
                    "Accessible without internet connectivity",
                  ],
                },
              ].map((contribution, idx) => (
                <div
                  key={idx}
                  className="bg-white border border-slate-200 rounded-xl p-6 hover:border-teal-300 transition-colors"
                >
                  <h3 className="font-semibold text-lg text-slate-900 mb-3">{contribution.title}</h3>
                  <ul className="space-y-2 text-slate-600 text-sm">
                    {contribution.items.map((item, itemIdx) => (
                      <li key={itemIdx} className="flex items-start gap-2">
                        <span className="w-1.5 h-1.5 rounded-full bg-teal-500 mt-2 flex-shrink-0" />
                        <span>{item}</span>
                      </li>
                    ))}
                  </ul>
                </div>
              ))}
            </div>
          </div>
        </section>
      </main>
      <Footer />
    </>
  )
}
