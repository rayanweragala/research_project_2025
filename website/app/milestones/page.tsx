import { Navigation } from "@/components/navigation";
import { Footer } from "@/components/footer";
import {
  CheckCircle2,
  Award,
  Calendar,
  Zap,
  Code,
  Brain,
  Smartphone,
  Server,
  BookOpen,
  Rocket,
  Trophy,
  Target,
} from "lucide-react";
export default function Milestones() {
  const milestones = [
    {
      phase: "Phase 1: Research & Planning",
      duration: "Months 1-2",
      status: "completed",
      items: [
        "Literature review and competitive analysis",
        "User research and requirements gathering",
        "Technology stack selection (Python, Java, OpenCV, TensorFlow)",
        "Project planning and resource allocation",
      ],
    },
    {
      phase: "Phase 2: Prototype Development",
      duration: "Months 3-5",
      status: "completed",
      items: [
        "Hardware integration and setup (cameras, sensors)",
        "Core vision module development with OpenCV",
        "AI model training (InsightFace, YOLO, EasyOCR)",
        "Initial prototype assembly and testing",
      ],
    },
    {
      phase: "Phase 3: Feature Implementation",
      duration: "Months 6-8",
      status: "completed",
      items: [
        "Face recognition system (Port 5000)",
        "Obstacle detection with ultrasonic sensors (Port 5001)",
        "OCR and text reading module (Port 5002)",
        "Voice command interface and haptic feedback",
      ],
    },
    {
      phase: "Phase 4: Testing & Refinement",
      duration: "Months 9-10",
      status: "completed",
      items: [
        "User acceptance testing with visually impaired users",
        "Performance optimization and edge computing",
        "Bug fixes and system refinements",
        "Accessibility compliance verification",
      ],
    },
    {
      phase: "Phase 5: Deployment & Documentation",
      duration: "Months 11-12",
      status: "completed",
      items: [
        "Final prototype finalization and packaging",
        "Comprehensive technical documentation",
        "User manual and setup guides creation",
        "Project presentation and commercialization planning",
      ],
    },
  ];

  return (
    <>
      <Navigation />
      <main>
        <section className="bg-gradient-to-br from-slate-900 via-slate-800 to-teal-900 py-20 md:py-28 relative overflow-hidden">
          <div className="absolute inset-0 bg-[url('data:image/svg+xml;base64,PHN2ZyB3aWR0aD0iNjAiIGhlaWdodD0iNjAiIHZpZXdCb3g9IjAgMCA2MCA2MCIgeG1sbnM9Imh0dHA6Ly93d3cudzMub3JnLzIwMDAvc3ZnIj48ZyBmaWxsPSJub25lIiBmaWxsLXJ1bGU9ImV2ZW5vZGQiPjxwYXRoIGQ9Ik0zNiAxOGMzLjMxNCAwIDYgMi42ODYgNiA2cy0yLjY4NiA2LTYgNi02LTIuNjg2LTYtNiAyLjY4Ni02IDYtNiIgc3Ryb2tlPSJyZ2JhKDI1NSwyNTUsMjU1LDAuMSkiLz48L2c+PC9zdmc+')] opacity-20"></div>

          <div className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8 relative">
            <div className="inline-flex items-center gap-2 bg-teal-500/20 backdrop-blur-sm px-4 py-2 rounded-full mb-6 border border-teal-400/30">
              <Trophy className="w-5 h-5 text-teal-300" />
              <span className="text-white font-semibold">
                All Phases Completed Successfully
              </span>
            </div>

            <h1 className="text-4xl md:text-6xl font-bold mb-6 text-white">
              Project Milestones
            </h1>
            <p className="text-xl text-slate-300 text-balance max-w-2xl leading-relaxed">
              A comprehensive timeline showcasing our journey from initial
              research to final deployment — 12 months of innovation,
              development, and refinement.
            </p>

            <div className="mt-10 grid grid-cols-3 gap-6 max-w-2xl">
              <div className="bg-white/10 backdrop-blur-sm rounded-xl p-4 text-center border border-white/20">
                <div className="text-3xl font-bold text-white">5</div>
                <div className="text-sm text-slate-300 mt-1">Phases</div>
              </div>
              <div className="bg-white/10 backdrop-blur-sm rounded-xl p-4 text-center border border-white/20">
                <div className="text-3xl font-bold text-white">12</div>
                <div className="text-sm text-slate-300 mt-1">Months</div>
              </div>
              <div className="bg-white/10 backdrop-blur-sm rounded-xl p-4 text-center border border-white/20">
                <div className="text-3xl font-bold text-white">100%</div>
                <div className="text-sm text-slate-300 mt-1">Complete</div>
              </div>
            </div>
          </div>
        </section>

        {/* Timeline Section */}
        <section className="py-20 md:py-28 bg-gradient-to-b from-slate-50 to-white">
          <div className="max-w-5xl mx-auto px-4 sm:px-6 lg:px-8">
            <div className="text-center mb-16">
              <h2 className="text-3xl md:text-4xl font-bold text-slate-900 mb-4">
                Development Timeline
              </h2>
              <p className="text-lg text-slate-600 max-w-2xl mx-auto">
                From conception to completion, every milestone achieved
              </p>
            </div>

            <div className="space-y-6">
              {milestones.map((milestone, idx) => (
                <div key={idx} className="relative group">
                  {idx !== milestones.length - 1 && (
                    <div className="absolute left-6 top-20 w-1 h-full bg-gradient-to-b from-teal-500 to-teal-300" />
                  )}

                  <div className="flex gap-6">
                    <div className="flex flex-col items-center">
                      <div className="relative">
                        <CheckCircle2 className="w-12 h-12 text-teal-500 flex-shrink-0" />
                        <div className="absolute inset-0 bg-teal-400 rounded-full blur-xl opacity-20 group-hover:opacity-40 transition-opacity"></div>
                      </div>
                    </div>

                    <div className="flex-1 bg-white border-2 border-slate-200 rounded-xl p-8 hover:border-teal-400 hover:shadow-xl transition-all duration-300 group-hover:-translate-y-1">
                      <div className="flex items-start justify-between mb-6 flex-wrap gap-4">
                        <div>
                          <h3 className="text-2xl font-bold text-slate-900 mb-2">
                            {milestone.phase}
                          </h3>
                          <div className="flex items-center gap-2 text-slate-600">
                            <Calendar className="w-4 h-4" />
                            <p className="text-sm font-medium">
                              {milestone.duration}
                            </p>
                          </div>
                        </div>
                        <span className="px-4 py-2 rounded-full text-sm font-semibold bg-teal-500 text-white shadow-md whitespace-nowrap flex items-center gap-2">
                          <CheckCircle2 className="w-4 h-4" />
                          Completed
                        </span>
                      </div>

                      <ul className="space-y-3">
                        {milestone.items.map((item, itemIdx) => (
                          <li
                            key={itemIdx}
                            className="flex items-start gap-3 text-slate-700 bg-slate-50 rounded-lg p-3 hover:bg-teal-50 transition-colors"
                          >
                            <CheckCircle2 className="w-5 h-5 text-teal-500 mt-0.5 flex-shrink-0" />
                            <span className="leading-relaxed">{item}</span>
                          </li>
                        ))}
                      </ul>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          </div>
        </section>

        {/* Deliverables Section */}
        <section className="py-20 md:py-28 bg-slate-900 text-white">
          <div className="max-w-6xl mx-auto px-4 sm:px-6 lg:px-8">
            <div className="text-center mb-16">
              <h2 className="text-3xl md:text-4xl font-bold mb-4">
                Key Deliverables
              </h2>
              <p className="text-xl text-slate-400">
                Six major outcomes from our development journey
              </p>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
              {[
                {
                  title: "Working Prototype",
                  desc: "Fully functional smart glasses with all features integrated and tested",
                  icon: Target,
                },
                {
                  title: "AI Models",
                  desc: "Trained and optimized ML models for face recognition, OCR, and object detection",
                  icon: Brain,
                },
                {
                  title: "Mobile App",
                  desc: "Android application with voice commands, sensor control, and real-time feedback",
                  icon: Smartphone,
                },
                {
                  title: "Server Backend",
                  desc: "Three Flask services running on ports 5000, 5001, and 5002 for AI processing",
                  icon: Server,
                },
                {
                  title: "Documentation",
                  desc: "Comprehensive technical documentation, user guides, and API references",
                  icon: BookOpen,
                },
                {
                  title: "Presentation",
                  desc: "Project presentation materials and detailed commercialization strategy",
                  icon: Rocket,
                },
              ].map((deliverable, idx) => {
                const Icon = deliverable.icon;
                return (
                  <div
                    key={idx}
                    className="bg-slate-800 border border-slate-700 rounded-xl p-6 hover:border-teal-400 hover:shadow-xl hover:shadow-teal-500/10 transition-all duration-300 hover:-translate-y-2"
                  >
                    <div className="w-12 h-12 rounded-lg bg-gradient-to-br from-teal-500 to-teal-600 flex items-center justify-center mb-4">
                      <Icon className="w-6 h-6 text-white" />
                    </div>
                    <h3 className="font-bold text-xl text-white mb-3">
                      {deliverable.title}
                    </h3>
                    <p className="text-slate-400 leading-relaxed">
                      {deliverable.desc}
                    </p>
                  </div>
                );
              })}
            </div>
          </div>
        </section>

        <section className="py-20 md:py-28 bg-gradient-to-b from-white to-slate-50">
          <div className="max-w-5xl mx-auto px-4 sm:px-6 lg:px-8">
            <div className="text-center mb-16">
              <h2 className="text-3xl md:text-4xl font-bold text-slate-900 mb-4">
                Technology Integration Timeline
              </h2>
              <p className="text-lg text-slate-600">
                How we built and deployed our tech stack
              </p>
            </div>

            <div className="space-y-6">
              {[
                {
                  phase: "Phase 1-2: Foundation",
                  desc: "Setup Python environment, Android SDK, hardware integration with Raspberry Pi and camera modules",
                  icon: Code,
                  color: "from-blue-500 to-cyan-500",
                },
                {
                  phase: "Phase 3: Core Services",
                  desc: "Deploy Face Recognition (Port 5000), Ultrasonic Sensor (Port 5001), OCR Service (Port 5002) with Flask servers",
                  icon: Server,
                  color: "from-teal-500 to-emerald-500",
                },
                {
                  phase: "Phase 4-5: Optimization",
                  desc: "Performance tuning, edge computing optimization, user testing, and final production deployment",
                  icon: Zap,
                  color: "from-emerald-500 to-green-500",
                },
              ].map((item, idx) => {
                const Icon = item.icon;
                return (
                  <div
                    key={idx}
                    className="bg-white border-2 border-slate-200 rounded-xl p-8 hover:border-teal-400 hover:shadow-xl transition-all duration-300 hover:-translate-y-1 group"
                  >
                    <div className="flex items-start gap-6">
                      <div
                        className={`w-14 h-14 rounded-xl bg-gradient-to-br ${item.color} text-white flex items-center justify-center shadow-lg group-hover:scale-110 transition-transform flex-shrink-0`}
                      >
                        <Icon className="w-7 h-7" />
                      </div>
                      <div className="flex-1">
                        <h3 className="font-bold text-xl text-slate-900 mb-3">
                          {item.phase}
                        </h3>
                        <p className="text-slate-600 leading-relaxed">
                          {item.desc}
                        </p>
                      </div>
                      <CheckCircle2 className="w-6 h-6 text-teal-500 flex-shrink-0" />
                    </div>
                  </div>
                );
              })}
            </div>
          </div>
        </section>

        <section className="py-16 bg-gradient-to-r from-teal-600 to-teal-700">
          <div className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8 text-center">
            <Award className="w-16 h-16 text-white mx-auto mb-6" />
            <h2 className="text-3xl md:text-4xl font-bold text-white mb-4">
              Project Successfully Completed
            </h2>
            <p className="text-xl text-teal-100 mb-8 max-w-2xl mx-auto">
              All milestones achieved on schedule. The Blind Assistant platform
              is now ready for deployment and real-world testing.
            </p>
            <div className="flex justify-center gap-4 flex-wrap">
              <div className="bg-white/20 backdrop-blur-sm px-6 py-3 rounded-full border border-white/30 flex items-center gap-2">
                <CheckCircle2 className="w-4 h-4 text-white" />
                <span className="text-white font-semibold">
                  All Features Implemented
                </span>
              </div>
              <div className="bg-white/20 backdrop-blur-sm px-6 py-3 rounded-full border border-white/30 flex items-center gap-2">
                <CheckCircle2 className="w-4 h-4 text-white" />
                <span className="text-white font-semibold">
                  Testing Complete
                </span>
              </div>
              <div className="bg-white/20 backdrop-blur-sm px-6 py-3 rounded-full border border-white/30 flex items-center gap-2">
                <CheckCircle2 className="w-4 h-4 text-white" />
                <span className="text-white font-semibold">
                  Ready for Launch
                </span>
              </div>
            </div>
          </div>
        </section>
      </main>
      <Footer />
    </>
  );
}
