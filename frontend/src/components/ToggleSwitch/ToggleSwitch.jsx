import './ToggleSwitch.css'

/**
 * Toggle Switch component
 * @param {boolean}  checked  - whether it is on
 * @param {function} onChange - state change callback
 * @param {string}   label    - label text
 * @param {boolean}  disabled - whether it is disabled
 */
export default function ToggleSwitch({ checked, onChange, label, disabled }) {
  return (
    <label className={`ts-wrap${disabled ? ' ts-disabled' : ''}`}>
      <input
        type="checkbox"
        className="ts-input"
        checked={checked}
        onChange={(e) => onChange?.(e.target.checked)}
        disabled={disabled}
      />
      <span className="ts-track">
        <span className="ts-thumb" />
      </span>
      {label && <span className="ts-label">{label}</span>}
    </label>
  )
}
