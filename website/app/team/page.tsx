'use client';

import { Navigation } from "@/components/navigation";
import { Footer } from "@/components/footer";
import { Mail, Linkedin, Github } from "lucide-react";

function TeamMemberAvatar({ member }) {
  return (
    <>
      <img
        src={member.image}
        alt={`${member.name}, ${member.role}`}
        className="w-14 h-14 rounded-full object-cover flex-shrink-0 bg-slate-200"
        onError={(e) => {
          e.target.style.display = 'none';
          e.target.nextSibling.style.display = 'flex';
        }}
      />
      <div className="w-14 h-14 rounded-full bg-gradient-to-br from-teal-500 to-teal-600 text-white flex items-center justify-center text-xl font-bold flex-shrink-0 hidden">
        {member.name.charAt(0)}
      </div>
    </>
  );
}

export default function Team() {
  const teamMembers = [
    {
      name: "Weragala R.T.L",
      id: "IT21820946",
      role: "Face Recognition Specialist",
      component: "Component 01: Real-Time Facial Recognition",
      focus:
        "Face recognition with personalized voice feedback, dynamic enrollment, edge AI optimization",
      image: "/rayan.jpg",
      linkedin: "https://lk.linkedin.com/in/rayan-weragala",
      github: "https://github.com/rayanweragala",
      email: "rayanthilakshana2000@gmail.com",
    },
    {
      name: "Dilini K.D.",
      id: "IT21826740",
      role: "Sinhala OCR Developer",
      component: "Component 03: Sinhala Text Recognition (OCR)",
      focus:
        "Optical character recognition, document identification, voice feedback for reading",
      image: "/dilini.jpeg",
      linkedin: "https://www.linkedin.com/in/k-d-dilini-863317282/",
      github: "https://github.com/IT21826740",
      email: "dilini@gmial.com",  
    },
    {
      name: "A.S.G. Punchihewa",
      id: "IT21821486",
      role: "Navigation System Developer",
      component: "Component 02: Sinhala Speech Navigation",
      focus:
        "Speech-to-text, text-to-speech, ultrasonic obstacle detection for safe navigation",
      image: "/asaka.jpeg",
      linkedin: "https://www.linkedin.com/in/asgp2000/",
      github: "https://github.com/ASGP",
      email: "asaka@gmail.com",
    },
    {
      name: "Vithanage H.P.",
      id: "IT21159190",
      role: "System Integration Lead",
      component: "Component 04: Scene Recognition & Object Detection",
      focus:
        "Mobile app development, hardware integration, system deployment, scene understanding",
      image: "/pevi.jpeg",
      linkedin: "https://www.linkedin.com/in/pevinya-vithanage-5981a625a/",
      github: "https://github.com/Pevi-Vitha",
      email: "pevi@gmail.com",
    },
  ];

  const supervisors = [
    {
      name: "Dr. Dharshana Kasthurirathna",
      title: "Supervisor",
      department: "Faculty of Computing | Computer Science",
      bio: "Senior Lecturer specializing in AI, machine learning, and edge computing applications for assistive technology.",
    },
    {
      name: "Ms. Hansi De Silva",
      title: "Co-Supervisor",
      department: "Faculty of Computing | Software Engineering",
      bio: "Lecturer in Software Engineering with expertise in human-computer interaction, accessibility, and mobile application development.",
    },
  ];

  return (
   <>
      <Navigation />
      <main>
        <section className="bg-gradient-to-br from-slate-900 via-slate-800 to-teal-900/20 py-16 md:py-24">
          <div className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8">
            <h1 className="text-4xl md:text-5xl font-bold mb-6 text-balance text-white">
              Research Team
            </h1>
            <p className="text-lg text-slate-300 text-balance max-w-2xl mb-4">
              The research team consists of undergraduate students specializing
              in TinyML, Edge AI, and assistive technology development.
            </p>
          </div>
        </section>

        <section className="py-16 md:py-24 bg-white">
          <div className="max-w-6xl mx-auto px-4 sm:px-6 lg:px-8">
            <h2 className="text-3xl font-bold mb-4 text-slate-900">
              Student Researchers
            </h2>
            <p className="text-slate-600 mb-12 max-w-3xl">
              Four undergraduate researchers from SLIIT's Department of Computer
              Systems and Engineering, each specializing in a critical component
              of the integrated assistive technology system.
            </p>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
              {teamMembers.map((member, idx) => (
                <div
                  key={idx}
                  className="bg-gradient-to-br from-slate-50 to-white border border-slate-200 rounded-xl overflow-hidden hover:shadow-lg hover:border-teal-300 transition-all"
                >
                  <div className="p-6">
                    <div className="flex items-start gap-4 mb-4">
                      <TeamMemberAvatar member={member} />
                      <div className="flex-1">
                        <h3 className="font-semibold text-lg text-slate-900">
                          {member.name}
                        </h3>
                        <p className="text-sm text-slate-500 mb-1">
                          {member.id}
                        </p>
                        <p className="text-teal-600 text-sm font-medium">
                          {member.role}
                        </p>
                      </div>
                    </div>

                    <div className="mb-3">
                      <span className="text-xs font-medium text-teal-700 bg-teal-50 px-3 py-1.5 rounded-full inline-block">
                        {member.component}
                      </span>
                    </div>

                    <p className="text-slate-600 text-sm mb-4 leading-relaxed">
                      {member.focus}
                    </p>

                    <div className="flex gap-2 pt-3 border-t border-slate-100">
                      {member.email && (
                        <a
                          href={`mailto:${member.email}`}
                          className="p-2 hover:bg-teal-50 rounded-lg transition-colors"
                          aria-label={`Email ${member.name}`}
                        >
                          <Mail
                            size={18}
                            className="text-slate-600 hover:text-teal-600"
                          />
                        </a>
                      )}
                      <a
                        href={member.linkedin}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="p-2 hover:bg-teal-50 rounded-lg transition-colors"
                        aria-label={`LinkedIn profile of ${member.name}`}
                      >
                        <Linkedin
                          size={18}
                          className="text-slate-600 hover:text-teal-600"
                        />
                      </a>
                      <a
                        href={member.github}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="p-2 hover:bg-teal-50 rounded-lg transition-colors"
                        aria-label={`GitHub profile of ${member.name}`}
                      >
                        <Github
                          size={18}
                          className="text-slate-600 hover:text-teal-600"
                        />
                      </a>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          </div>
        </section>

        <section className="py-16 md:py-24 bg-slate-50">
          <div className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8">
            <h2 className="text-3xl font-bold mb-12 text-slate-900">
              Academic Supervision
            </h2>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-8 mb-8">
              {supervisors.map((supervisor, idx) => (
                <div
                  key={idx}
                  className="bg-white border border-slate-200 rounded-xl p-8 hover:border-teal-300 transition-colors"
                >
                  <div className="w-12 h-12 rounded-full bg-gradient-to-br from-teal-100 to-slate-100 flex items-center justify-center text-teal-600 font-bold text-xl mb-4">
                    {supervisor.name.split(" ")[0].charAt(0)}
                  </div>
                  <h3 className="text-xl font-semibold mb-2 text-slate-900">
                    {supervisor.name}
                  </h3>
                  <p className="text-teal-600 font-medium mb-1">
                    {supervisor.title}
                  </p>
                  <p className="text-slate-500 text-sm mb-4">
                    {supervisor.department}
                  </p>
                  <p className="text-slate-600 leading-relaxed">
                    {supervisor.bio}
                  </p>
                </div>
              ))}
            </div>

            <div className="bg-gradient-to-r from-teal-50 to-slate-50 border border-teal-200 rounded-xl p-8">
              <h3 className="font-semibold text-lg text-slate-900 mb-4">
                Institution Details
              </h3>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-6 text-sm">
                <div>
                  <p className="font-medium text-slate-900 mb-1">Institution</p>
                  <p className="text-slate-600">
                    Sri Lanka Institute of Information Technology (SLIIT)
                  </p>
                </div>
                <div>
                  <p className="font-medium text-slate-900 mb-1">Department</p>
                  <p className="text-slate-600">
                    Computer Systems and Engineering
                  </p>
                </div>
                <div>
                  <p className="font-medium text-slate-900 mb-1">
                    Degree Program
                  </p>
                  <p className="text-slate-600">
                    B.Sc. (Hons) in Information Technology
                  </p>
                </div>
                <div>
                  <p className="font-medium text-slate-900 mb-1">
                    Project Code
                  </p>
                  <p className="text-slate-600">R25-012</p>
                </div>
              </div>
            </div>
          </div>
        </section>

        <section className="py-16 md:py-24 bg-white">
          <div className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8">
            <h2 className="text-3xl font-bold mb-12 text-slate-900">
              Research Values & Approach
            </h2>
            <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
              {[
                {
                  title: "User-Centered Design",
                  desc: "Developing with and for visually impaired individuals, incorporating feedback at every stage to ensure real-world usability.",
                },
                {
                  title: "Privacy First",
                  desc: "All AI processing occurs on-device using Edge AI, ensuring user data remains private and secure without cloud dependency.",
                },
                {
                  title: "Accessibility & Affordability",
                  desc: "Creating cost-effective solutions (~Rs. 70,000) that are 10x cheaper than commercial alternatives, accessible to developing regions.",
                },
              ].map((value, idx) => (
                <div
                  key={idx}
                  className="bg-gradient-to-br from-slate-50 to-white border border-slate-200 rounded-xl p-6 hover:border-teal-300 transition-colors"
                >
                  <div className="w-10 h-10 rounded-full bg-teal-100 flex items-center justify-center text-teal-600 font-bold text-lg mb-4">
                    {idx + 1}
                  </div>
                  <h3 className="text-xl font-semibold mb-3 text-slate-900">
                    {value.title}
                  </h3>
                  <p className="text-slate-600 leading-relaxed">{value.desc}</p>
                </div>
              ))}
            </div>
          </div>
        </section>

        <section className="py-16 md:py-24 bg-slate-50">
          <div className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8">
            <h2 className="text-3xl font-bold mb-8 text-slate-900">
              Collaborative Research
            </h2>
            <div className="bg-white border border-slate-200 rounded-xl p-8">
              <p className="text-slate-600 leading-relaxed mb-6">
                This research project represents a collaborative effort where
                each team member developed a specialized component that
                integrates seamlessly into the unified IoT Smart Glasses system.
                The modular architecture allows each component to function
                independently while contributing to the comprehensive assistive
                solution.
              </p>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                {[
                  { label: "Research Duration", value: "8 months (2024-2025)" },
                  { label: "Total Components", value: "4 integrated modules" },
                  {
                    label: "Technologies Used",
                    value: "TinyML, Edge AI, TensorFlow Lite",
                  },
                  {
                    label: "Target Platform",
                    value: "Raspberry Pi 5 + Android",
                  },
                ].map((item, idx) => (
                  <div key={idx} className="flex items-start gap-3">
                    <div className="w-1.5 h-1.5 rounded-full bg-teal-500 mt-2 flex-shrink-0" />
                    <div>
                      <p className="font-medium text-slate-900">{item.label}</p>
                      <p className="text-slate-600 text-sm">{item.value}</p>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          </div>
        </section>

        <section className="py-16 md:py-24 bg-gradient-to-r from-slate-900 via-teal-900 to-slate-900 text-white">
          <div className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8 text-center space-y-6">
            <h2 className="text-3xl font-bold text-balance">
              Connect With Our Team
            </h2>
            <p className="text-lg opacity-90 text-balance max-w-2xl mx-auto">
              Interested in our research? Have questions about the technology or
              collaboration opportunities? We welcome inquiries from
              researchers, industry partners, and organizations working in
              assistive technology.
            </p>
            <div className="flex flex-col sm:flex-row gap-4 justify-center pt-4">
              <a
                href="mailto:rayanthilakshana2000@gmail.com"
                className="inline-flex items-center justify-center gap-2 bg-white text-slate-900 px-8 py-3 rounded-lg font-semibold hover:bg-slate-100 transition-all"
              >
                <Mail size={20} />
                Contact Research Team
              </a>
              <a
                href="https://lk.linkedin.com/in/rayan-weragala"
                target="_blank"
                rel="noopener noreferrer"
                className="inline-flex items-center justify-center gap-2 border-2 border-white text-white px-8 py-3 rounded-lg font-semibold hover:bg-white/10 transition-all"
              >
                <Linkedin size={20} />
                Connect on LinkedIn
              </a>
            </div>
          </div>
        </section>
      </main>
      <Footer />
    </>
  );
}