export function Footer() {
  return (
    <footer className="bg-secondary text-secondary-foreground py-12 mt-20">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="grid grid-cols-1 md:grid-cols-3 gap-8 mb-8">
          <div>
            <h3 className="font-bold text-lg mb-4">Blind Assistant Research</h3>
            <p className="text-sm opacity-90">
              Advancing assistive technology for visually impaired individuals through innovative smart glasses
              solutions.
            </p>
          </div>
          <div>
            <h4 className="font-semibold mb-4">Quick Links</h4>
            <ul className="space-y-2 text-sm">
              <li>
                <a href="/" className="hover:underline">
                  Home
                </a>
              </li>
              <li>
                <a href="/about" className="hover:underline">
                  About
                </a>
              </li>
              <li>
                <a href="/team" className="hover:underline">
                  Our Team
                </a>
              </li>
            </ul>
          </div>
          <div>
            <h4 className="font-semibold mb-4">Resources</h4>
            <ul className="space-y-2 text-sm">
              <li>
                <a href="/documentation" className="hover:underline">
                  Documentation
                </a>
              </li>
              <li>
                <a href="/scope" className="hover:underline">
                  Project Scope
                </a>
              </li>
            </ul>
          </div>
        </div>
        <div className="border-t border-secondary-foreground/20 pt-8 text-center text-sm opacity-75">
          <p>&copy; 2025 Blind Assistant. All rights reserved.</p>
        </div>
      </div>
    </footer>
  )
}
