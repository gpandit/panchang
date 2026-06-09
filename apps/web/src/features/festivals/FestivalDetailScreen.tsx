// TODO(design): skin via Aqualeo design system. Structure, a11y, and token
// wiring are final — only className/visual treatment changes.

import Link from "next/link";
import { FestivalShareBar } from "./FestivalShareBar";
import type { FestivalDetailOut } from "./types";

interface FestivalDetailScreenProps {
  festival: FestivalDetailOut;
}

export function FestivalDetailScreen({ festival }: FestivalDetailScreenProps): React.JSX.Element {
  return (
    <main aria-label={`Festival detail: ${festival.name}`} className="flex flex-col min-h-screen">
      <header className="px-md py-sm border-b border-border flex items-center gap-sm">
        <Link
          href="/festivals"
          className="text-sm text-muted-foreground hover:text-foreground"
          aria-label="Back to festival list"
        >
          ← Festivals
        </Link>
      </header>

      <article className="flex flex-col gap-md px-md py-md flex-1">
        <div className="flex flex-col gap-xs">
          <h1 className="text-lg font-semibold">{festival.name}</h1>
          {festival.date ? (
            <time dateTime={festival.date} className="text-xs text-muted-foreground">
              {festival.date}
            </time>
          ) : null}
          {festival.description ? (
            <p className="text-sm text-muted-foreground">{festival.description}</p>
          ) : null}

          {festival.tags.length > 0 ? (
            <div className="flex gap-xs flex-wrap" aria-label="Festival tags">
              {festival.tags.map((tag: string) => (
                <span
                  key={tag}
                  className="text-xs px-xs py-0.5 rounded-sm bg-muted text-muted-foreground capitalize"
                >
                  {tag}
                </span>
              ))}
            </div>
          ) : null}
        </div>

        {festival.body ? (
          <Section heading="About">
            <p className="text-sm leading-relaxed whitespace-pre-line">{festival.body}</p>
          </Section>
        ) : null}

        {festival.puja ? (
          <Section heading="Puja Vidhi">
            <p className="text-sm leading-relaxed whitespace-pre-line">{festival.puja}</p>
          </Section>
        ) : null}

        {festival.katha ? (
          <Section heading="Katha">
            <p className="text-sm leading-relaxed whitespace-pre-line">{festival.katha}</p>
          </Section>
        ) : null}
      </article>

      <FestivalShareBar festivalId={festival.id} festivalName={festival.name} />
    </main>
  );
}

function Section({
  heading,
  children,
}: {
  heading: string;
  children: React.ReactNode;
}): React.JSX.Element {
  return (
    <section aria-labelledby={`section-${heading.toLowerCase().replace(/\s+/g, "-")}`}>
      <h2
        id={`section-${heading.toLowerCase().replace(/\s+/g, "-")}`}
        className="text-xs font-semibold text-muted-foreground uppercase tracking-wide mb-xs"
      >
        {heading}
      </h2>
      {children}
    </section>
  );
}
