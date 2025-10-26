"use client";

import { useState, useEffect } from "react";
import { Navigation } from "@/components/navigation";
import { Footer } from "@/components/footer";
import {
  Download,
  ExternalLink,
  FileText,
  Presentation,
  BookOpen,
  FolderOpen,
} from "lucide-react";

export default function Documentation() {
  const [origin, setOrigin] = useState("");

  useEffect(() => {
    setOrigin(typeof window !== "undefined" ? window.location.origin : "");
  }, []);

  const documentsSection = [
    {
      category: "Project Proposal",
      icon: FileText,
      items: [
        {
          title: "Proposal Report - IT21820946",
          desc: "Initial project proposal by Weragala R.T.L",
          file: "Proposal-Report_R25_012_IT21820946.pdf",
        },
        {
          title: "Proposal Report - IT21821486",
          desc: "Initial project proposal by Member 2",
          file: "Proposal-Report_R25_012_IT21821486.pdf",
        },
        {
          title: "Proposal Report - IT21826740",
          desc: "Initial project proposal by Member 3",
          file: "Proposal-Report_R25_012_IT21826740.pdf",
        },
        {
          title: "Proposal Report - IT21823220",
          desc: "Initial project proposal by Member 4",
          file: "Proposal-Report_R25_012_IT21823220.pdf",
        },
      ],
    },
    {
      category: "Logbook",
      icon: BookOpen,
      items: [
        {
          title: "Logbook - IT21820946",
          desc: "Project logbook by Weragala R.T.L",
          file: "logbook-member1.pdf",
        },
        {
          title: "Logbook - IT21821486",
          desc: "Project logbook by Member 2",
          file: "logbook-member2.pdf",
        },
        {
          title: "Logbook - IT21826740",
          desc: "Project logbook by Member 3",
          file: "logbook-member3.pdf",
        },
        {
          title: "Logbook - IT21823220",
          desc: "Project logbook by Member 4",
          file: "logbook-member4.pdf",
        },
      ],
    },
    {
      category: "Final Report",
      icon: FileText,
      items: [
        {
          title: "Final Report - IT21820946",
          desc: "Final project report by Weragala R.T.L",
          file: "IT21820946_FinalReport.pdf",
        },
        {
          title: "Final Report - IT21821486",
          desc: "Final project report by Member 2",
          file: "IT21821486_FinalReport.pdf",
        },
        {
          title: "Final Report - IT21826740",
          desc: "Final project report by Member 3",
          file: "IT21826740_FinalReport.pdf",
        },
        {
          title: "Final Report - IT21823220",
          desc: "Final project report by Member 4",
          file: "IT21823220_FinalReport.pdf",
        },
      ],
    },
  ];

  const presentationsSection = [
    {
      category: "Presentations",
      icon: Presentation,
      items: [
        {
          title: "Progress Presentation 01",
          desc: "First progress update presentation",
          file: "R25_012_PP1.pptx",
        },
        {
          title: "Progress Presentation 02",
          desc: "Second progress update presentation",
          file: "PP2_R025_012.pptx",
        },
      ],
    },
  ];

  const allSections = [...documentsSection, ...presentationsSection];

  const getIconForType = (file) => {
    if (file.endsWith(".pdf")) return <FileText className="w-4 h-4" />;
    if (file.endsWith(".pptx")) return <Presentation className="w-4 h-4" />;
    return <FileText className="w-4 h-4" />;
  };

  const fileToViewUrl = {
    "Proposal-Report_R25_012_IT21820946.pdf":
      "https://www.dropbox.com/scl/fi/6hoy4grkt35sql3gsk8bq/Proposal-Report_R25_012_IT21820946.pdf?rlkey=kzal5gxu61aiwyw0mo231k0ul&st=vm9ngl6z&dl=0",
    "Proposal-Report_R25_012_IT21821486.pdf":
      "https://www.dropbox.com/scl/fi/014ch26y7wnerltymbpjc/Proposal-Report_R25-012_IT21821486.pdf?rlkey=ffefpnwbmbimc3qfy3hts3aiy&st=3xrzjmzl&dl=0",
    "Proposal-Report_R25_012_IT21826740.pdf":
      "https://www.dropbox.com/scl/fi/x5y9mywfitrjlibo5bey9/Proposal-report_R25-012_IT21826740.pdf?rlkey=wcb1di2wh2z2zfzf9v0mtx0dk&st=w734t6vn&dl=0",
    "Proposal-Report_R25_012_IT21823220.pdf":
      "https://www.dropbox.com/scl/fi/j9cvkb914z6l2u1fiztus/Proposal-report_R25-012_IT21823220.pdf?rlkey=td3f4efh896mp4so9cirat8ut&st=vxmexcdb&dl=0",
    "logbook-member1.pdf":
      "https://www.dropbox.com/scl/fi/[your-folder-id]/logbook-member1.pdf?rlkey=[your-rlkey]&st=[your-st]&dl=0",
    "logbook-member2.pdf":
      "https://www.dropbox.com/scl/fi/[your-folder-id]/logbook-member2.pdf?rlkey=[your-rlkey]&st=[your-st]&dl=0",
    "logbook-member3.pdf":
      "https://www.dropbox.com/scl/fi/[your-folder-id]/logbook-member3.pdf?rlkey=[your-rlkey]&st=[your-st]&dl=0",
    "logbook-member4.pdf":
      "https://www.dropbox.com/scl/fi/[your-folder-id]/logbook-member4.pdf?rlkey=[your-rlkey]&st=[your-st]&dl=0",
    "IT21820946_FinalReport.pdf":
      "https://www.dropbox.com/scl/fi/li25lrp2is98bpnboe0zt/IT21820946_FinalReport.pdf?rlkey=ewampeodo4gi8dum4a1towxoe&st=9w7ztkyp&dl=0",
    "IT21821486_FinalReport.pdf":
      "https://www.dropbox.com/scl/fi/a22dyw1kowcpk3eqgqri3/IT21821486_FinalReport.pdf?rlkey=rnbcybe28yencavypitlzg79l&st=k1xr67fq&dl=0",
    "IT21826740_FinalReport.pdf":
      "https://www.dropbox.com/scl/fi/a22dyw1kowcpk3eqgqri3/IT21821486_FinalReport.pdf?rlkey=rnbcybe28yencavypitlzg79l&st=xpxz9msy&dl=0",
    "IT21823220_FinalReport.pdf":
      "https://www.dropbox.com/scl/fi/[your-folder-id]/IT21823220_FinalReport.pdf?rlkey=[your-rlkey]&st=[your-st]&dl=0",
    "R25_012_PP1.pptx":
      "https://www.dropbox.com/scl/fi/9fvoqj8646x00rq4izf47/R25_012_PP1.pptx?rlkey=sbsvr3ybo7py6de2kwlpfgkbo&st=gejrnhwj&dl=0",
    "PP2_R025_012.pptx":
      "https://www.dropbox.com/scl/fi/c5wsk9bj02df8azw4doeo/PP2_R025_012.pptx?rlkey=78xj833f3z4lu0l8jwqy81ryc&st=urz2b9g7&dl=0",
  };

  const getViewUrl = (file) => {
    if (!origin) return `/documents/${file}`;
    const dropboxUrl = fileToViewUrl[file];
    return dropboxUrl || `${origin}/documents/${file}`;
  };

  const renderCategorySection = (cat, idx) => {
    const CatIcon = cat.icon;
    const bgClass = idx % 2 === 0 ? "bg-white" : "bg-slate-50";
    return (
      <section key={cat.category} className={`py-12 md:py-16 ${bgClass}`}>
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <h2 className="text-3xl font-bold flex items-center gap-3 text-slate-900 border-b border-slate-200 pb-4 mb-8">
            <CatIcon className="w-8 h-8 text-teal-500" />
            {cat.category}
          </h2>
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
            {cat.items.map((item, itemIdx) => (
              <div
                key={itemIdx}
                className="bg-gradient-to-br from-slate-50 to-white border border-slate-200 rounded-lg p-6 hover:shadow-lg hover:border-teal-300 transition-all group"
              >
                <div className="flex items-start justify-between mb-3">
                  <h4 className="font-semibold text-base text-slate-900 flex-1 group-hover:text-teal-600 transition-colors">
                    {item.title}
                  </h4>
                  <div className="flex items-center gap-1 text-slate-500 ml-3 flex-shrink-0">
                    {getIconForType(item.file)}
                  </div>
                </div>
                <p className="text-slate-600 text-sm mb-4">{item.desc}</p>
                <div className="flex items-center justify-between pt-4 border-t border-slate-200">
                  <span className="text-xs text-slate-500">
                    File: {item.file}
                  </span>
                  <div className="flex items-center gap-4">
                    <a
                      href={getViewUrl(item.file)}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="flex items-center gap-1 text-teal-600 text-sm font-medium hover:text-teal-700 transition-colors"
                    >
                      <ExternalLink size={16} />
                      View Online
                    </a>
                    <a
                      href={`/documents/${item.file}`}
                      download={item.file}
                      className="flex items-center gap-1 text-slate-600 text-sm font-medium hover:text-slate-700 transition-colors"
                    >
                      <Download size={16} />
                      Download
                    </a>
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>
      </section>
    );
  };

  return (
    <>
      <Navigation />
      <main>
        <section className="bg-gradient-to-br from-slate-900 via-slate-800 to-teal-900/20 py-16 md:py-24">
          <div className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8">
            <h1 className="text-4xl md:text-5xl font-bold mb-6 text-balance text-white">
              Project Documentation
            </h1>
            <p className="text-lg text-slate-300 text-balance max-w-2xl">
              Access our research reports, presentations, and logbooks. All
              documents are available for online viewing or download for
              reference.
            </p>
          </div>
        </section>

        {allSections.map(renderCategorySection)}

        <section className="py-16 md:py-24 bg-white">
          <div className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8">
            <h2 className="text-3xl font-bold mb-8 text-slate-900">
              Project Overview
            </h2>
            <div className="bg-gradient-to-br from-slate-50 to-white border border-slate-200 rounded-xl p-8">
              <p className="text-slate-600 text-sm mb-4">
                This project aims to assist people with visual impairments using
                an Android mobile application that connects to smart glasses and
                provides voice feedback, alongside a Python server handling face
                recognition, text reading (OCR), and ultrasonic distance
                sensing.
              </p>
              <a
                href="/documents/README.md"
                className="inline-flex items-center gap-2 text-teal-600 font-medium hover:text-teal-700 transition-colors"
              >
                Read Full README <ExternalLink size={16} />
              </a>
            </div>
          </div>
        </section>
      </main>
      <Footer />
    </>
  );
}
