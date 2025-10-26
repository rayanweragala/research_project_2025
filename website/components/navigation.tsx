"use client"

import Link from "next/link"
import { useState } from "react"
import { Menu, X } from "lucide-react"
import { usePathname } from "next/navigation"

export function Navigation() {
  const [isOpen, setIsOpen] = useState(false)
  const pathname = usePathname()

  const navItems = [
    { href: "/", label: "Home" },
    { href: "/about", label: "About" },
    { href: "/scope", label: "Scope" },
    { href: "/milestones", label: "Milestones" },
    { href: "/documentation", label: "Documentation" },
    { href: "/team", label: "Our Team" },
  ]

  const isActive = (href: string) => {
    if (href === "/") return pathname === "/"
    return pathname.startsWith(href)
  }

  return (
    <nav className="sticky top-0 z-50 bg-background/95 backdrop-blur-md border-b border-border/50 shadow-sm">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex justify-between items-center h-16">
          <Link
            href="/"
            className="flex items-center gap-2 font-bold text-xl text-primary hover:opacity-80 transition-opacity"
          >
            <div className="w-8 h-8 bg-gradient-to-br from-teal-500 to-teal-600 rounded-lg flex items-center justify-center text-white font-bold text-sm">
              BA
            </div>
            <span className="hidden sm:inline bg-gradient-to-r from-teal-600 to-slate-700 bg-clip-text text-transparent">
              Blind Assistant
            </span>
          </Link>

          <div className="hidden md:flex items-center gap-1">
            {navItems.map((item) => (
              <Link
                key={item.href}
                href={item.href}
                className={`px-4 py-2 text-sm font-medium rounded-lg transition-all duration-200 relative ${
                  isActive(item.href)
                    ? "text-teal-600 bg-teal-50"
                    : "text-slate-600 hover:text-teal-600 hover:bg-slate-50"
                }`}
              >
                {item.label}
                {isActive(item.href) && (
                  <div className="absolute bottom-0 left-4 right-4 h-0.5 bg-gradient-to-r from-teal-500 to-teal-600 rounded-full" />
                )}
              </Link>
            ))}
          </div>

          <button
            onClick={() => setIsOpen(!isOpen)}
            className="md:hidden p-2 hover:bg-slate-100 rounded-lg transition-colors"
            aria-label="Toggle menu"
          >
            {isOpen ? <X size={24} className="text-slate-700" /> : <Menu size={24} className="text-slate-700" />}
          </button>
        </div>

        {isOpen && (
          <div className="md:hidden pb-4 space-y-2 border-t border-border/50 pt-4">
            {navItems.map((item) => (
              <Link
                key={item.href}
                href={item.href}
                className={`block px-4 py-2 text-sm font-medium rounded-lg transition-all ${
                  isActive(item.href)
                    ? "text-teal-600 bg-teal-50"
                    : "text-slate-600 hover:text-teal-600 hover:bg-slate-50"
                }`}
                onClick={() => setIsOpen(false)}
              >
                {item.label}
              </Link>
            ))}
          </div>
        )}
      </div>
    </nav>
  )
}
