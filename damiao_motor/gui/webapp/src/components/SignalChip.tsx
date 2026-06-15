import { useDraggable } from "@dnd-kit/core";
import type { SignalDescriptor } from "../lib/types";
import { signalColor } from "../lib/format";

export default function SignalChip({ sig }: { sig: SignalDescriptor }) {
  const { attributes, listeners, setNodeRef, isDragging } = useDraggable({
    id: `sig:${sig.id}`,
    data: { signalId: sig.id },
  });
  const color = signalColor(sig);
  return (
    <div
      ref={setNodeRef}
      className={"sig-chip" + (isDragging ? " dragging" : "")}
      {...listeners}
      {...attributes}
      title={sig.id}
    >
      <span
        className="sig-swatch"
        style={{ background: color, borderStyle: sig.source === "cmd" ? "dashed" : "solid" }}
      />
      <span className="sig-name">
        {sig.source}.{sig.field}
      </span>
      {sig.unit && <span className="sig-unit">{sig.unit}</span>}
    </div>
  );
}
