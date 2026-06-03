import {
  useEffect,
  useId,
  useLayoutEffect,
  useMemo,
  useRef,
  useState,
} from "react";
import { createPortal } from "react-dom";
import type { CSSProperties } from "react";
import type { FieldOption } from "./types";

const EMPTY_LABEL = "— не выбрано";
/** padding trigger + chevron + запас */
const WIDTH_EXTRA_PX = 40;

type Props = {
  value: string;
  options: FieldOption[];
  onChange: (value: string) => void;
  title?: string;
};

function measureLabels(
  measureEl: HTMLSpanElement,
  font: string,
  labels: string[]
): number {
  measureEl.style.font = font;
  let max = 0;
  for (const text of labels) {
    measureEl.textContent = text;
    max = Math.max(max, measureEl.scrollWidth);
  }
  return max;
}

export function FieldSelect({ value, options, onChange, title }: Props) {
  const [open, setOpen] = useState(false);
  const [menuStyle, setMenuStyle] = useState<CSSProperties>({});
  const [controlWidth, setControlWidth] = useState<number | null>(null);
  const rootRef = useRef<HTMLDivElement>(null);
  const triggerRef = useRef<HTMLButtonElement>(null);
  const measureRef = useRef<HTMLSpanElement>(null);
  const listId = useId();

  const allLabels = useMemo(
    () => [EMPTY_LABEL, ...options.map((o) => o.label)],
    [options]
  );

  const recalcWidth = () => {
    const measure = measureRef.current;
    const trigger = triggerRef.current;
    if (!measure || !trigger) return;
    const font = getComputedStyle(trigger).font;
    const textWidth = measureLabels(measure, font, allLabels);
    setControlWidth(textWidth + WIDTH_EXTRA_PX);
  };

  useLayoutEffect(() => {
    recalcWidth();
  }, [allLabels]);

  useLayoutEffect(() => {
    const ro = new ResizeObserver(() => recalcWidth());
    if (triggerRef.current) ro.observe(triggerRef.current);
    return () => ro.disconnect();
  }, []);

  const updateMenuPosition = () => {
    const el = triggerRef.current;
    if (!el) return;
    const rect = el.getBoundingClientRect();
    const width = controlWidth ?? rect.width;
    setMenuStyle({
      position: "fixed",
      top: rect.bottom + 2,
      left: rect.left,
      width,
      zIndex: 9999,
    });
  };

  useEffect(() => {
    const onDocClick = (e: MouseEvent) => {
      const target = e.target as Node;
      if (rootRef.current?.contains(target)) return;
      const portal = document.getElementById(`menu-${listId}`);
      if (portal?.contains(target)) return;
      setOpen(false);
    };
    document.addEventListener("mousedown", onDocClick);
    return () => document.removeEventListener("mousedown", onDocClick);
  }, [listId]);

  useEffect(() => {
    if (!open) return;
    updateMenuPosition();
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") setOpen(false);
    };
    const onReflow = () => updateMenuPosition();
    document.addEventListener("keydown", onKey);
    window.addEventListener("resize", onReflow);
    window.addEventListener("scroll", onReflow, true);
    return () => {
      document.removeEventListener("keydown", onKey);
      window.removeEventListener("resize", onReflow);
      window.removeEventListener("scroll", onReflow, true);
    };
  }, [open, controlWidth]);

  const selected = options.find((o) => String(o.value) === value);
  const displayLabel = selected?.label ?? EMPTY_LABEL;

  const menu = open ? (
    <ul
      id={`menu-${listId}`}
      className="custom-select-menu"
      style={menuStyle}
      role="listbox"
    >
      <li
        role="option"
        aria-selected={value === ""}
        className={`custom-select-option custom-select-option--empty${value === "" ? " is-selected" : ""}`}
        onMouseDown={(e) => e.preventDefault()}
        onClick={() => {
          onChange("");
          setOpen(false);
        }}
      >
        {EMPTY_LABEL}
      </li>
      {options.map((o) => {
        const optValue = String(o.value);
        const isSelected = value === optValue;
        return (
          <li
            key={o.value}
            role="option"
            aria-selected={isSelected}
            className={`custom-select-option${isSelected ? " is-selected" : ""}`}
            onMouseDown={(e) => e.preventDefault()}
            onClick={() => {
              onChange(optValue);
              setOpen(false);
            }}
          >
            {o.label}
          </li>
        );
      })}
    </ul>
  ) : null;

  return (
    <div
      className={`custom-select${open ? " is-open" : ""}`}
      ref={rootRef}
      title={title}
      style={controlWidth != null ? { width: controlWidth } : undefined}
    >
      <span ref={measureRef} className="custom-select-measure" aria-hidden />
      <button
        ref={triggerRef}
        type="button"
        className="custom-select-trigger"
        aria-expanded={open}
        aria-haspopup="listbox"
        aria-controls={`menu-${listId}`}
        onClick={() => setOpen((v) => !v)}
      >
        <span
          className={
            value === "" ? "custom-select-label is-placeholder" : "custom-select-label"
          }
        >
          {displayLabel}
        </span>
        <span className="custom-select-chevron" aria-hidden />
      </button>

      {menu && createPortal(menu, document.body)}
    </div>
  );
}
