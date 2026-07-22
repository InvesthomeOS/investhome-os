export interface DateRangeValue {
  from: string;
  to: string;
}

export interface DateRangeControlProps {
  value: DateRangeValue;
  onChange: (value: DateRangeValue) => void;
  fromLabel: string;
  toLabel: string;
  className?: string;
}

export function DateRangeControl({
  value,
  onChange,
  fromLabel,
  toLabel,
  className,
}: DateRangeControlProps) {
  return (
    <div className={`ds-date-range${className ? ` ${className}` : ''}`}>
      <label className="ds-date-range__field">
        <span className="ds-date-range__label">{fromLabel}</span>
        <input
          type="date"
          className="ds-date-range__input"
          value={value.from}
          onChange={(event) => onChange({ ...value, from: event.target.value })}
        />
      </label>
      <label className="ds-date-range__field">
        <span className="ds-date-range__label">{toLabel}</span>
        <input
          type="date"
          className="ds-date-range__input"
          value={value.to}
          onChange={(event) => onChange({ ...value, to: event.target.value })}
        />
      </label>
    </div>
  );
}
