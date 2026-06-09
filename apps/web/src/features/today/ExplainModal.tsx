"use client";

// TODO(design): skin via Aqualeo design system. Structure, a11y, and token
// wiring are final — only className/visual treatment changes.

import { Modal } from "@/components/primitives";
import type { PanchangElement } from "@pandit/api-client-ts";

interface ExplainModalProps {
  element: PanchangElement | null;
  onClose: () => void;
}

export function ExplainModal({ element, onClose }: ExplainModalProps): React.JSX.Element {
  const HEADER_ID = "explain-modal-title";
  return (
    <Modal
      open={element !== null}
      onClose={onClose}
      labelledBy={HEADER_ID}
      size="md"
      header={
        <h2 id={HEADER_ID} className="text-lg font-display">
          {element?.label ?? ""}
        </h2>
      }
      body={
        <div className="flex flex-col gap-sm text-sm">
          <p className="font-semibold">{element?.value}</p>
          {element?.explanation ? (
            <p className="text-muted-foreground">{element.explanation}</p>
          ) : (
            <p className="text-muted-foreground italic">
              Explanation coming soon — content is sourced from the CMS.
            </p>
          )}
        </div>
      }
      footer={
        <button
          type="button"
          className="text-sm text-primary underline"
          onClick={onClose}
          aria-label="Close explanation"
        >
          Close
        </button>
      }
    />
  );
}
