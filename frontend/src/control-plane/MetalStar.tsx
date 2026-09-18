import { useId } from "react";

/** Original faceted geometry, shaded without images or a WebGL render loop. */
export function MetalStar({ className = "" }: { className?: string }) {
  const id = useId().replace(/:/g, "");
  const outer =
    "M160 8C187 104 208 129 312 160C210 188 187 210 160 312C132 210 108 186 8 160C109 132 133 109 160 8Z";
  const inner =
    "M160 57C179 119 198 140 261 160C199 179 179 200 160 263C140 200 120 181 57 160C119 140 140 121 160 57Z";
  return (
    <svg
      className={`br-metal ${className}`}
      viewBox="0 0 340 340"
      fill="none"
      aria-hidden="true"
    >
      <defs>
        <linearGradient
          id={`${id}-edge`}
          x1="18"
          y1="25"
          x2="280"
          y2="310"
          gradientUnits="userSpaceOnUse"
        >
          <stop stopColor="#f8f8f8" />
          <stop offset=".18" stopColor="#323536" />
          <stop offset=".3" stopColor="#e2e5e6" />
          <stop offset=".46" stopColor="#676b6d" />
          <stop offset=".52" stopColor="#fff" />
          <stop offset=".62" stopColor="#383c3d" />
          <stop offset=".83" stopColor="#d6d9da" />
          <stop offset="1" stopColor="#52595b" />
        </linearGradient>
        <linearGradient
          id={`${id}-face`}
          x1="250"
          y1="20"
          x2="72"
          y2="295"
          gradientUnits="userSpaceOnUse"
        >
          <stop stopColor="#6d7375" />
          <stop offset=".13" stopColor="#f9fafb" />
          <stop offset=".29" stopColor="#191c1d" />
          <stop offset=".39" stopColor="#c7cdcf" />
          <stop offset=".5" stopColor="#fff" />
          <stop offset=".57" stopColor="#414648" />
          <stop offset=".7" stopColor="#070a0b" />
          <stop offset=".81" stopColor="#f2f4f4" />
          <stop offset="1" stopColor="#464b4c" />
        </linearGradient>
        <mask id={`${id}-hole`}>
          <rect width="340" height="340" fill="white" />
          <path d={inner} fill="black" />
        </mask>
      </defs>
      <g transform="translate(10 7)">
        <path
          d={outer}
          transform="translate(7 10)"
          fill={`url(#${id}-edge)`}
          mask={`url(#${id}-hole)`}
        />
        <path
          d={outer}
          fill={`url(#${id}-face)`}
          stroke="#d6d9db"
          strokeWidth="1.3"
          mask={`url(#${id}-hole)`}
        />
        <path d={inner} stroke={`url(#${id}-edge)`} strokeWidth="6" />
        <path
          d="M160 8L160 57M312 160L261 160M160 312L160 263M8 160L57 160"
          stroke="#f1f4f5"
          strokeWidth="1.4"
        />
        <path
          d="M160 13C179 114 204 144 304 160M12 160C113 176 145 208 160 304"
          stroke="#ffffff"
          strokeOpacity=".45"
          strokeWidth="2"
        />
      </g>
    </svg>
  );
}
