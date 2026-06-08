import type { ReactNode } from "react";

// TODO(design): skin via Aqualeo design system. Structure, a11y, and token
// wiring are final — only className/visual treatment changes.

export interface FooterLink {
  href: string;
  label: ReactNode;
}

interface FooterProps {
  links: FooterLink[];
  legal?: ReactNode;
  social?: ReactNode;
  className?: string;
}

export function Footer({ links, legal, social, className = "" }: FooterProps): React.JSX.Element {
  return (
    <footer className={`flex flex-col gap-md p-md text-sm text-muted-foreground ${className}`.trim()}>
      <ul className="flex flex-row gap-md">
        {links.map((link) => (
          <li key={link.href}>
            <a href={link.href}>{link.label}</a>
          </li>
        ))}
      </ul>
      {social ? <div>{social}</div> : null}
      {legal ? <p>{legal}</p> : null}
    </footer>
  );
}
