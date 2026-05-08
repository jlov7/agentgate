import Link from "next/link";
import { Bezel, SectionHeading, ShellBand } from "@agentgate/ui";

export default function ReferencePage() {
  return (
    <main>
      <ShellBand className="py-10">
        <SectionHeading eyebrow="Reference migration" title="MkDocs remains the source of reference truth during the console migration." copy="The new console is the product surface. Existing docs stay available as the technical reference until each workflow has a console-native replacement." />
      </ShellBand>
      <ShellBand className="pb-20">
        <Bezel innerClassName="p-8">
          <div className="grid gap-4 md:grid-cols-2">
            <Link className="rounded-2xl border border-graphite-900/10 bg-bone-100/70 p-5 transition hover:border-verdigris-500/35" href="/reference/GET_STARTED/">
              Start here reference
            </Link>
            <Link className="rounded-2xl border border-graphite-900/10 bg-bone-100/70 p-5 transition hover:border-verdigris-500/35" href="/reference/HOSTED_SANDBOX/">
              Hosted sandbox reference
            </Link>
          </div>
        </Bezel>
      </ShellBand>
    </main>
  );
}
