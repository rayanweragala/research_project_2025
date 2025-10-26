import { Navigation } from "@/components/navigation";
import { Footer } from "@/components/footer";
import {
  CheckCircle,
  Code,
  Cpu,
  Smartphone,
  Camera,
  Users,
  TrendingUp,
  Award,
  Globe,
} from "lucide-react";
import Image from "next/image";

export default function About() {
  return (
    <>
      <Navigation />
      <main>
        <section className="bg-gradient-to-br from-slate-900 via-slate-800 to-teal-900/20 py-16 md:py-24">
          <div className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8">
            <h1 className="text-4xl md:text-5xl font-bold mb-6 text-balance text-white">
              About Project
            </h1>
            <p className="text-lg text-slate-300 text-balance mb-4 max-w-2xl">
              A research initiative focused on developing intelligent wearable
              smart glasses that provide real-time facial recognition,
              navigation, and scene understanding using TinyML and Edge AI —
              improving independence for visually impaired individuals.
            </p>
          </div>
        </section>

        <section className="py-16 md:py-24 bg-white">
          <div className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8">
            <div className="grid grid-cols-1 md:grid-cols-2 gap-8 items-center">
              <div>
                <h2 className="text-3xl font-bold mb-8 text-slate-900">
                  The Challenge
                </h2>
                <div className="space-y-6 text-slate-600">
                  <div className="bg-teal-50 border border-teal-200 rounded-lg p-4">
                    <p className="text-teal-900 font-semibold mb-2">
                      Global Impact
                    </p>
                    <p className="text-teal-800 text-sm">
                      Over 285 million people worldwide live with visual
                      impairment, with approximately 39 million categorized as
                      blind (WHO, 2022). In Sri Lanka, nearly 75% of cases
                      affect individuals over 40 years old.
                    </p>
                  </div>
                  <p>
                    Visually impaired individuals face significant barriers in
                    daily life: recognizing familiar faces in social settings,
                    navigating safely through environments with obstacles, and
                    reading printed Sinhala text independently. Traditional aids
                    like white canes and guide dogs provide mobility support but
                    lack intelligent awareness of people and surroundings.
                  </p>
                  <p>
                    Existing commercial solutions like OrCam MyEye ($3,500+) and
                    Microsoft Seeing AI are either prohibitively expensive or
                    lack support for the Sinhala language and offline
                    functionality critical for Sri Lankan users in areas with
                    limited internet connectivity.
                  </p>
                </div>
              </div>
              <div className="relative h-80 bg-gradient-to-br from-teal-100 to-slate-100 rounded-xl overflow-hidden border border-slate-200">
                <Image
                  src="/visually-impaired-person-navigating-with-assistanc.jpg"
                  alt="Visually impaired individual navigating with assistance"
                  fill
                  className="object-cover"
                  sizes="(max-width: 768px) 100vw, 50vw"
                />
              </div>
            </div>
          </div>
        </section>

        <section className="py-16 md:py-24 bg-slate-50">
          <div className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8">
            <div className="grid grid-cols-1 md:grid-cols-2 gap-8 items-center">
              <div className="relative h-80 bg-gradient-to-br from-teal-100 to-slate-100 rounded-xl overflow-hidden border border-slate-200 order-2 md:order-1">
                <Image
                  src="/smart-glasses-technology-solution-for-blind-users.jpg"
                  alt="Smart glasses with integrated camera and sensors for assistive technology"
                  fill
                  className="object-cover"
                  sizes="(max-width: 768px) 100vw, 50vw"
                />
              </div>
              <div className="order-1 md:order-2">
                <h2 className="text-3xl font-bold mb-8 text-slate-900">
                  Our Integrated Solution
                </h2>
                <p className="text-slate-600 mb-6">
                  A comprehensive assistive system combining smart glasses with
                  a mobile application, powered by TinyML and Edge AI to deliver
                  three core capabilities designed specifically for the Sri
                  Lankan visually impaired community.
                </p>
                <div className="space-y-4">
                  {[
                    {
                      title: "Real-Time Facial Recognition",
                      desc: "Identify known individuals with 92% accuracy and personalized whisper feedback. Dynamic enrollment via voice commands.",
                    },
                    {
                      title: "Sinhala Voice Navigation",
                      desc: "Speech-to-text commands (75-85% accuracy) with ultrasonic obstacle detection up to 1 meter. Real-time audio warnings.",
                    },
                    {
                      title: "Sinhala Text Recognition & Reading",
                      desc: "OCR for printed Sinhala text with document classification (exam papers, newspapers, forms, notes, stories, words) and TTS conversion.",
                    },
                  ].map((item, idx) => (
                    <div
                      key={idx}
                      className="bg-white border border-slate-200 rounded-lg p-4 flex items-start gap-3 hover:border-teal-300 transition-colors"
                    >
                      <CheckCircle className="w-5 h-5 text-teal-500 flex-shrink-0 mt-1" />
                      <div>
                        <h3 className="font-semibold text-slate-900">
                          {item.title}
                        </h3>
                        <p className="text-slate-600 text-sm">{item.desc}</p>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            </div>
          </div>
        </section>

        <section className="py-16 md:py-24 bg-white">
          <div className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8">
            <h2 className="text-3xl font-bold mb-4 text-slate-900">
              Technology Architecture
            </h2>
            <p className="text-slate-600 mb-12">
              Built on Edge AI principles for privacy, affordability, and
              offline functionality
            </p>
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
              {[
                {
                  icon: Smartphone,
                  title: "Mobile App",
                  items: [
                    "Android/React Native",
                    "Voice command interface",
                    "Frame filtering logic",
                    "Bluetooth communication",
                    "Accessibility features",
                  ],
                },
                {
                  icon: Cpu,
                  title: "Edge Server",
                  items: [
                    "Flask REST API",
                    "Python 3.10+",
                    "Systemd service",
                    "Local Wi-Fi network",
                    "Static IP configuration",
                  ],
                },
                {
                  icon: Code,
                  title: "AI/ML Models",
                  items: [
                    "FaceNet/MobileFaceNet",
                    "TensorFlow Lite (float16)",
                    "Whisper (Sinhala STT)",
                    "Google ML Kit/Tesseract",
                    "Transfer learning",
                  ],
                },
                {
                  icon: Camera,
                  title: "IoT Hardware",
                  items: [
                    "Raspberry Pi 5 (BCM2712)",
                    "8GB RAM, 8 TOPS",
                    "Pi Camera Module 2 (8MP)",
                    "HC-SR04 sensors",
                    "27W USB-C power",
                  ],
                },
              ].map((tech, idx) => {
                const Icon = tech.icon;
                return (
                  <div
                    key={idx}
                    className="bg-gradient-to-br from-teal-50 to-slate-50 border border-teal-200 rounded-xl p-6 hover:shadow-lg transition-shadow"
                  >
                    <div className="flex items-center gap-3 mb-4">
                      <Icon className="w-6 h-6 text-teal-500" />
                      <h3 className="font-semibold text-lg text-slate-900">
                        {tech.title}
                      </h3>
                    </div>
                    <ul className="space-y-2 text-slate-600 text-sm">
                      {tech.items.map((item, itemIdx) => (
                        <li key={itemIdx} className="flex items-start gap-2">
                          <span className="w-1 h-1 rounded-full bg-teal-500 mt-1.5 flex-shrink-0" />
                          <span>{item}</span>
                        </li>
                      ))}
                    </ul>
                  </div>
                );
              })}
            </div>
          </div>
        </section>

        <section className="py-16 md:py-24 bg-slate-50">
          <div className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8">
            <h2 className="text-3xl font-bold mb-12 text-slate-900">
              Research Achievements
            </h2>
            <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-12">
              {[
                {
                  icon: TrendingUp,
                  stat: "92%",
                  label: "Face Recognition Accuracy",
                  detail: "Controlled conditions",
                },
                {
                  icon: Award,
                  stat: "<1s",
                  label: "Inference Latency",
                  detail: "Real-time performance",
                },
                {
                  icon: Users,
                  stat: "Rs. 70K",
                  label: "Total System Cost",
                  detail: "vs OrCam's $3,500+",
                },
              ].map((achievement, idx) => (
                <div
                  key={idx}
                  className="bg-white border border-slate-200 rounded-xl p-6 text-center hover:shadow-lg transition-shadow"
                >
                  <achievement.icon className="w-10 h-10 text-teal-500 mx-auto mb-3" />
                  <div className="text-3xl font-bold text-slate-900 mb-1">
                    {achievement.stat}
                  </div>
                  <div className="font-semibold text-slate-700 mb-1">
                    {achievement.label}
                  </div>
                  <div className="text-sm text-slate-500">
                    {achievement.detail}
                  </div>
                </div>
              ))}
            </div>

            <h3 className="text-2xl font-bold mb-6 text-slate-900">
              Key Performance Metrics
            </h3>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
              {[
                {
                  title: "Facial Recognition Module",
                  metrics: [
                    "Controlled accuracy: 92%",
                    "Real-world accuracy: 85%",
                    "False positive rate: <7%",
                    "Dynamic enrollment: Voice-activated",
                  ],
                },
                {
                  title: "Navigation System",
                  metrics: [
                    "Sinhala STT accuracy: 75-85%",
                    "Obstacle detection: 2cm-1m range",
                    "Response latency: <1s",
                    "Offline operation: 100%",
                  ],
                },
                {
                  title: "OCR & Document Recognition",
                  metrics: [
                    "Sinhala OCR accuracy: 68% (controlled)",
                    "Document classification: 78% accuracy",
                    "6 document types supported",
                    "TTS integration: Natural voice",
                  ],
                },
                {
                  title: "System Performance",
                  metrics: [
                    "End-to-end latency: <1.5s",
                    "Frame processing: 1-2 FPS",
                    "Privacy: 100% on-device",
                    "Cost efficiency: 10x cheaper",
                  ],
                },
              ].map((category, idx) => (
                <div
                  key={idx}
                  className="bg-white border border-slate-200 rounded-xl p-6 hover:border-teal-300 transition-colors"
                >
                  <h4 className="font-semibold text-lg text-slate-900 mb-3">
                    {category.title}
                  </h4>
                  <ul className="space-y-2 text-slate-600 text-sm">
                    {category.metrics.map((metric, metricIdx) => (
                      <li key={metricIdx} className="flex items-start gap-2">
                        <CheckCircle className="w-4 h-4 text-teal-500 flex-shrink-0 mt-0.5" />
                        <span>{metric}</span>
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
            <h2 className="text-3xl font-bold mb-8 text-slate-900 flex items-center gap-3">
              <Globe className="w-8 h-8 text-teal-500" />
              Impact & Future Directions
            </h2>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-6 mb-8">
              <div className="bg-white border border-slate-200 rounded-xl p-6">
                <h3 className="font-semibold text-lg text-slate-900 mb-3">
                  Social Impact
                </h3>
                <ul className="space-y-2 text-slate-600 text-sm">
                  {[
                    "Empowers 285M+ visually impaired individuals globally",
                    "Promotes independence and social confidence",
                    "Bridges accessibility gap in Sri Lanka",
                    "Affordable alternative to expensive commercial solutions",
                    "Localized for Sinhala-speaking community",
                  ].map((impact, idx) => (
                    <li key={idx} className="flex items-start gap-2">
                      <CheckCircle className="w-4 h-4 text-teal-500 flex-shrink-0 mt-0.5" />
                      <span>{impact}</span>
                    </li>
                  ))}
                </ul>
              </div>

              <div className="bg-white border border-slate-200 rounded-xl p-6">
                <h3 className="font-semibold text-lg text-slate-900 mb-3">
                  Future Enhancements
                </h3>
                <ul className="space-y-2 text-slate-600 text-sm">
                  {[
                    "Infrared cameras for low-light recognition",
                    "Advanced attention mechanisms for occlusions",
                    "FAISS library for scalable database lookup",
                    "GPS integration for outdoor navigation",
                    "Multi-language support (Tamil, English)",
                    "Cloud backup with user consent",
                  ].map((future, idx) => (
                    <li key={idx} className="flex items-start gap-2">
                      <span className="w-1.5 h-1.5 rounded-full bg-teal-500 mt-1.5 flex-shrink-0" />
                      <span>{future}</span>
                    </li>
                  ))}
                </ul>
              </div>
            </div>

            <div className="bg-gradient-to-r from-teal-500 to-teal-600 text-white rounded-xl p-8 text-center">
              <h3 className="text-2xl font-bold mb-3">Research Contribution</h3>
              <p className="text-teal-50 max-w-2xl mx-auto">
                This research advances intelligent, real-time assistance systems
                by demonstrating that IoT Smart Glasses and Mobile Applications
                can operate efficiently in low-power, privacy-sensitive
                environments while maintaining high accuracy and reliability for
                visually impaired individuals in developing regions.
              </p>
            </div>
          </div>
        </section>
      </main>
      <Footer />
    </>
  );
}
