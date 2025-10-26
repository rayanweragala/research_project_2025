import { Navigation } from "@/components/navigation";
import { Footer } from "@/components/footer";
import { CheckCircle2, Circle } from "lucide-react";

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
      status: "in-progress",
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
      status: "upcoming",
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
      status: "upcoming",
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
        <section className="bg-gradient-to-br from-slate-900 via-slate-800 to-teal-900/20 py-16 md:py-24">
          <div className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8">
            <h1 className="text-4xl md:text-5xl font-bold mb-6 text-balance text-white">
              Project Milestones
            </h1>
            <p className="text-lg text-slate-300 text-balance max-w-2xl">
              A timeline showcasing our key development phases — from initial
              research and design, through model training and hardware
              integration, to system testing and final deployment.
            </p>
          </div>
        </section>

        <section className="py-16 md:py-24 bg-white">
          <div className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8">
            <div className="space-y-8">
              {milestones.map((milestone, idx) => (
                <div key={idx} className="relative">
                  {idx !== milestones.length - 1 && (
                    <div className="absolute left-6 top-16 w-1 h-20 bg-gradient-to-b from-teal-500 to-teal-300 opacity-30" />
                  )}

                  <div className="flex gap-6">
                    <div className="flex flex-col items-center">
                      {milestone.status === "completed" ? (
                        <CheckCircle2 className="w-12 h-12 text-teal-500 flex-shrink-0" />
                      ) : milestone.status === "in-progress" ? (
                        <div className="w-12 h-12 rounded-full border-4 border-teal-500 flex items-center justify-center flex-shrink-0">
                          <div className="w-6 h-6 rounded-full bg-teal-500 animate-pulse" />
                        </div>
                      ) : (
                        <Circle className="w-12 h-12 text-slate-300 flex-shrink-0" />
                      )}
                    </div>
                    <div className="flex-1 bg-gradient-to-br from-slate-50 to-white border border-slate-200 rounded-lg p-6 hover:border-teal-300 transition-colors">
                      <div className="flex items-start justify-between mb-4">
                        <div>
                          <h3 className="text-xl font-semibold text-slate-900">
                            {milestone.phase}
                          </h3>
                          <p className="text-sm text-slate-600">
                            {milestone.duration}
                          </p>
                        </div>
                        <span
                          className={`px-3 py-1 rounded-full text-xs font-semibold whitespace-nowrap ${
                            milestone.status === "completed"
                              ? "bg-teal-100 text-teal-700"
                              : milestone.status === "in-progress"
                              ? "bg-teal-100 text-teal-700"
                              : "bg-slate-100 text-slate-600"
                          }`}
                        >
                          {milestone.status === "completed"
                            ? "Completed"
                            : milestone.status === "in-progress"
                            ? "In Progress"
                            : "Upcoming"}
                        </span>
                      </div>
                      <ul className="space-y-2">
                        {milestone.items.map((item, itemIdx) => (
                          <li
                            key={itemIdx}
                            className="flex items-start gap-3 text-slate-600"
                          >
                            <span className="text-teal-500 font-bold mt-0.5">
                              •
                            </span>
                            <span>{item}</span>
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

        <section className="py-16 md:py-24 bg-slate-50">
          <div className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8">
            <h2 className="text-3xl font-bold mb-8 text-slate-900">
              Key Deliverables
            </h2>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
              {[
                {
                  title: "Working Prototype",
                  desc: "Fully functional smart glasses with all features",
                },
                {
                  title: "AI Models",
                  desc: "Trained and optimized ML models for production",
                },
                {
                  title: "Mobile App",
                  desc: "Android application with voice and sensor control",
                },
                {
                  title: "Server Backend",
                  desc: "Three Flask services for AI processing",
                },
                {
                  title: "Documentation",
                  desc: "Comprehensive technical and user guides",
                },
                {
                  title: "Presentation",
                  desc: "Project presentation and commercialization plan",
                },
              ].map((deliverable, idx) => (
                <div
                  key={idx}
                  className="bg-white border border-slate-200 rounded-lg p-6 hover:shadow-lg hover:border-teal-300 transition-all"
                >
                  <div className="w-10 h-10 rounded-full bg-gradient-to-br from-teal-500 to-teal-600 text-white flex items-center justify-center font-semibold mb-3">
                    {idx + 1}
                  </div>
                  <h3 className="font-semibold text-lg text-slate-900 mb-2">
                    {deliverable.title}
                  </h3>
                  <p className="text-slate-600 text-sm">{deliverable.desc}</p>
                </div>
              ))}
            </div>
          </div>
        </section>

        <section className="py-16 md:py-24 bg-white">
          <div className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8">
            <h2 className="text-3xl font-bold mb-8 text-slate-900">
              Technology Integration Timeline
            </h2>
            <div className="space-y-4">
              {[
                {
                  phase: "Phase 1-2: Foundation",
                  desc: "Setup Python environment, Android SDK, hardware integration",
                },
                {
                  phase: "Phase 3: Core Services",
                  desc: "Deploy Face Recognition (5000), Ultrasonic (5001), OCR (5002) servers",
                },
                {
                  phase: "Phase 4-5: Optimization",
                  desc: "Performance tuning, edge computing optimization, final deployment",
                },
              ].map((item, idx) => (
                <div
                  key={idx}
                  className="bg-gradient-to-r from-teal-50 to-slate-50 border border-teal-200 rounded-xl p-6 hover:shadow-lg transition-shadow"
                >
                  <h3 className="font-semibold text-slate-900 mb-2">
                    {item.phase}
                  </h3>
                  <p className="text-slate-600 text-sm">{item.desc}</p>
                </div>
              ))}
            </div>
          </div>
        </section>
      </main>
      <Footer />
    </>
  );
}
