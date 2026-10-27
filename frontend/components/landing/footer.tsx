import type { SVGProps } from "react";

const navLinks = [
  { label: "Products", href: "#" },
  { label: "Studio", href: "#" },
  { label: "Clients", href: "#" },
  { label: "Pricing", href: "#pricing" },
  { label: "Blog", href: "#" },
  { label: "Privacy", href: "#" },
  { label: "Terms", href: "#" },
];

function PublicVaultLogo() {
  return (
    <div className="flex h-[48px] w-[48px] items-center justify-center rounded-[11px] bg-[#17171a]">
      <svg
        width="30"
        height="30"
        viewBox="0 0 24 24"
        fill="none"
        stroke="#ffffff"
        strokeWidth={1.6}
        strokeLinecap="round"
        strokeLinejoin="round"
        aria-hidden="true"
      >
        <path d="M4.5 9.5v-2a2 2 0 0 1 2-2h11a2 2 0 0 1 2 2v2" />
        <path d="M4.5 9.5h15v2.6a7.5 7.5 0 0 1-7.5 7.5 7.5 7.5 0 0 1-7.5-7.5v-2.6Z" />
        <path d="M12 12v4.6M9.9 13.7h4.2" />
      </svg>
    </div>
  );
}

function XIcon(props: SVGProps<SVGSVGElement>) {
  return (
    <svg
      width={30}
      height={30}
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth={1.8}
      strokeLinecap="round"
      aria-hidden="true"
      {...props}
    >
      <path d="M4 4l16 16M20 4L4 20" />
    </svg>
  );
}

function LinkedInIcon(props: SVGProps<SVGSVGElement>) {
  return (
    <svg width={30} height={30} viewBox="0 0 24 24" fill="currentColor" aria-hidden="true" {...props}>
      <path d="M20.447 20.452h-3.554v-5.569c0-1.328-.027-3.037-1.852-3.037-1.853 0-2.136 1.445-2.136 2.939v5.667H9.351V9h3.414v1.561h.046c.477-.9 1.637-1.85 3.37-1.85 3.601 0 4.267 2.37 4.267 5.455v6.286zM5.337 7.433a2.062 2.062 0 0 1-2.063-2.065 2.064 2.064 0 1 1 2.063 2.065zm1.782 13.019H3.555V9h3.564v11.452zM22.225 0H1.771C.792 0 0 .774 0 1.729v20.542C0 23.227.792 24 1.771 24h20.451C23.2 24 24 23.227 24 22.271V1.729C24 .774 23.2 0 22.225 0z" />
    </svg>
  );
}

function GitHubIcon(props: SVGProps<SVGSVGElement>) {
  return (
    <svg width={30} height={30} viewBox="0 0 24 24" fill="currentColor" aria-hidden="true" {...props}>
      <path d="M12 .297c-6.63 0-12 5.373-12 12 0 5.303 3.438 9.8 8.205 11.385.6.113.82-.258.82-.577 0-.285-.01-1.04-.015-2.04-3.338.724-4.042-1.61-4.042-1.61C4.422 18.07 3.633 17.7 3.633 17.7c-1.087-.744.084-.729.084-.729 1.205.084 1.838 1.236 1.838 1.236 1.07 1.835 2.809 1.305 3.495.998.108-.776.417-1.305.76-1.605-2.665-.3-5.466-1.332-5.466-5.93 0-1.31.465-2.38 1.235-3.22-.135-.303-.54-1.523.105-3.176 0 0 1.005-.322 3.3 1.23.96-.267 1.98-.399 3-.405 1.02.006 2.04.138 3 .405 2.28-1.552 3.285-1.23 3.285-1.23.645 1.653.24 2.873.12 3.176.765.84 1.23 1.91 1.23 3.22 0 4.61-2.805 5.625-5.475 5.92.42.36.81 1.096.81 2.22 0 1.606-.015 2.896-.015 3.286 0 .315.21.69.825.57C20.565 22.092 24 17.592 24 12.297c0-6.627-5.373-12-12-12" />
    </svg>
  );
}

function FacebookIcon(props: SVGProps<SVGSVGElement>) {
  return (
    <svg width={30} height={30} viewBox="0 0 24 24" fill="currentColor" aria-hidden="true" {...props}>
      <path d="M24 12.073c0-6.627-5.373-12-12-12s-12 5.373-12 12c0 5.99 4.388 10.954 10.125 11.854v-8.385H7.078v-3.47h3.047V9.43c0-3.007 1.792-4.669 4.533-4.669 1.312 0 2.686.235 2.686.235v2.953H15.83c-1.491 0-1.956.925-1.956 1.874v2.25h3.328l-.532 3.47h-2.796v8.385C19.612 23.027 24 18.062 24 12.073z" />
    </svg>
  );
}

function InstagramIcon(props: SVGProps<SVGSVGElement>) {
  return (
    <svg width={30} height={30} viewBox="0 0 24 24" fill="currentColor" aria-hidden="true" {...props}>
      <path d="M12 0C8.74 0 8.333.015 7.053.072 5.775.132 4.905.333 4.14.63c-.789.306-1.459.717-2.126 1.384S.935 3.35.63 4.14C.333 4.905.131 5.775.072 7.053.012 8.333 0 8.74 0 12s.015 3.667.072 4.947c.06 1.277.261 2.148.558 2.913.306.788.717 1.459 1.384 2.126.667.666 1.336 1.079 2.126 1.384.766.296 1.636.499 2.913.558C8.333 23.988 8.74 24 12 24s3.667-.015 4.947-.072c1.277-.06 2.148-.262 2.913-.558.788-.306 1.459-.718 2.126-1.384.666-.667 1.079-1.335 1.384-2.126.296-.765.499-1.636.558-2.913.06-1.28.072-1.687.072-4.947s-.015-3.667-.072-4.947c-.06-1.277-.262-2.149-.558-2.913-.306-.789-.718-1.459-1.384-2.126C21.319 1.347 20.651.935 19.86.63c-.765-.297-1.636-.499-2.913-.558C15.667.012 15.26 0 12 0zm0 2.16c3.203 0 3.585.016 4.85.071 1.17.055 1.805.249 2.227.415.562.217.96.477 1.382.896.419.42.679.819.896 1.381.164.422.36 1.057.413 2.227.057 1.266.07 1.646.07 4.85s-.015 3.585-.074 4.85c-.061 1.17-.256 1.805-.421 2.227-.224.562-.479.96-.899 1.382-.419.419-.824.679-1.38.896-.42.164-1.065.36-2.235.413-1.274.057-1.649.07-4.859.07-3.211 0-3.586-.015-4.859-.074-1.171-.061-1.816-.256-2.236-.421-.569-.224-.96-.479-1.379-.899-.421-.419-.69-.824-.9-1.38-.165-.42-.359-1.065-.42-2.235-.045-1.26-.061-1.649-.061-4.844 0-3.196.016-3.586.061-4.861.061-1.17.255-1.814.42-2.234.21-.57.479-.96.9-1.381.419-.419.81-.689 1.379-.898.42-.166 1.051-.361 2.221-.421 1.275-.045 1.65-.06 4.859-.06l.045.03zm0 3.678c-3.405 0-6.162 2.76-6.162 6.162 0 3.405 2.76 6.162 6.162 6.162 3.405 0 6.162-2.76 6.162-6.162 0-3.405-2.76-6.162-6.162-6.162zM12 16c-2.21 0-4-1.79-4-4s1.79-4 4-4 4 1.79 4 4-1.79 4-4 4zm7.846-10.405c0 .795-.646 1.44-1.44 1.44-.795 0-1.44-.646-1.44-1.44 0-.794.646-1.439 1.44-1.439.793-.001 1.44.645 1.44 1.439z" />
    </svg>
  );
}

const socials = [
  { name: "Twitter", href: "#", Icon: XIcon },
  { name: "LinkedIn", href: "#", Icon: LinkedInIcon },
  { name: "GitHub", href: "#", Icon: GitHubIcon },
  { name: "Facebook", href: "#", Icon: FacebookIcon },
  { name: "Instagram", href: "#", Icon: InstagramIcon },
];

export function Footer() {
  return (
    <footer className="w-full border-t border-[#ededed] bg-background">
      <div className="mx-auto w-full max-w-[1300px] px-[26px] max-sm:px-5">
        {/* Top divider — inset 26px, large empty space below */}
        <div className="pt-[68px]">
          <div className="h-px w-full bg-[#e7e7e7]" />
        </div>

        {/* Brand + navigation */}
        <div className="flex flex-col items-center">
          {/* Brand */}
          <div className="mt-[132px] flex items-center">
            <PublicVaultLogo />
            <span className="ml-[12px] text-[21px] font-semibold leading-none text-[#17171a]">
              FamilyVault
            </span>
          </div>

          {/* Navigation */}
          <nav
            aria-label="Footer navigation"
            className="mt-[38px] flex flex-wrap items-center justify-center gap-x-[40px] gap-y-4"
          >
            {navLinks.map((item) => (
              <a
                key={item.label}
                href={item.href}
                className="text-[21px] leading-7 text-[#4b4b4b] transition-colors hover:text-black"
              >
                {item.label}
              </a>
            ))}
          </nav>
        </div>

        {/* Dashed divider */}
        <div className="mt-[62px] border-t border-dashed border-[#e3e3e3]" />

        {/* Bottom row */}
        <div className="flex items-center justify-between py-[52px] max-md:flex-col max-md:gap-7">
          <p className="m-0 text-[20px] leading-6 text-[#6b6b6b]">
            © FamilyVault 2026
          </p>

          <div className="flex items-center gap-[25px]">
            {socials.map(({ name, href, Icon }) => (
              <a
                key={name}
                href={href}
                aria-label={name}
                className="flex h-[30px] w-[30px] items-center justify-center text-[#8d8d8d] transition-colors hover:text-[#17171a]"
              >
                <Icon width={30} height={30} />
              </a>
            ))}
          </div>
        </div>
      </div>
    </footer>
  );
}