import { useEffect, useRef, useState } from "react";
import { createPortal } from "react-dom";
import { GridStack, type GridStackNode } from "gridstack";
import "gridstack/dist/gridstack.min.css";

import { useWidgets, type Widget } from "../lib/widgets";
import { PANEL_BY_KIND } from "../panels/registry";

function WidgetFrame({ widget, onRemove }: { widget: Widget; onRemove: () => void }) {
  const def = PANEL_BY_KIND[widget.kind];
  return (
    <div className="widget">
      <div className="widget-header">
        <span className="widget-grip" aria-hidden>⠿</span>
        <span className="widget-icon">{def?.icon}</span>
        <span className="widget-title">{def?.title || widget.kind}</span>
        <button className="widget-close" title="Remove widget" onClick={onRemove}>
          ×
        </button>
      </div>
      <div className="widget-body">{def ? def.render(widget.id) : null}</div>
    </div>
  );
}

export default function Canvas() {
  const widgets = useWidgets((s) => s.widgets);
  const updateGeom = useWidgets((s) => s.updateGeom);
  const removeWidget = useWidgets((s) => s.removeWidget);

  const rootRef = useRef<HTMLDivElement | null>(null);
  const gridRef = useRef<GridStack | null>(null);
  const itemEls = useRef<Map<string, HTMLElement>>(new Map());
  const [contentEls, setContentEls] = useState<Map<string, HTMLElement>>(new Map());
  const [ready, setReady] = useState(false);

  // init GridStack once
  useEffect(() => {
    if (!rootRef.current) return;
    const grid = GridStack.init(
      {
        column: 12,
        cellHeight: 56,
        margin: 8,
        float: true,
        handle: ".widget-header",
        resizable: { handles: "e, se, s, sw, w" },
        animate: true,
      },
      rootRef.current
    );
    gridRef.current = grid;

    grid.on("change", (_e, nodes) => {
      const geoms = (nodes as GridStackNode[]).map((n) => ({
        id: String(n.id),
        x: n.x ?? 0,
        y: n.y ?? 0,
        w: n.w ?? 1,
        h: n.h ?? 1,
      }));
      if (geoms.length) updateGeom(geoms);
    });

    setReady(true);
    return () => {
      grid.destroy(false);
      gridRef.current = null;
    };
  }, [updateGeom]);

  // reconcile widget list -> gridstack items (add new, remove gone)
  useEffect(() => {
    const grid = gridRef.current;
    if (!grid || !ready) return;

    const wanted = new Set(widgets.map((w) => w.id));
    let changed = false;
    const nextContent = new Map(contentEls);

    // add new
    grid.batchUpdate();
    for (const w of widgets) {
      if (itemEls.current.has(w.id)) continue;
      const el = grid.addWidget({ x: w.x, y: w.y, w: w.w, h: w.h, id: w.id });
      const content = el.querySelector(".grid-stack-item-content") as HTMLElement;
      itemEls.current.set(w.id, el);
      nextContent.set(w.id, content);
      changed = true;
    }
    // remove gone
    for (const [id, el] of Array.from(itemEls.current.entries())) {
      if (!wanted.has(id)) {
        grid.removeWidget(el, true);
        itemEls.current.delete(id);
        nextContent.delete(id);
        changed = true;
      }
    }
    grid.commit();

    if (changed) setContentEls(nextContent);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [widgets, ready]);

  return (
    <div className="canvas">
      <div className="grid-stack" ref={rootRef} />
      {widgets.map((w) => {
        const c = contentEls.get(w.id);
        return c
          ? createPortal(
              <WidgetFrame widget={w} onRemove={() => removeWidget(w.id)} />,
              c,
              w.id
            )
          : null;
      })}
    </div>
  );
}
