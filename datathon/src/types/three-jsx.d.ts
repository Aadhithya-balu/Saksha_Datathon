import type { ThreeElements } from '@react-three/fiber';

// @react-three/fiber v8 augments the legacy global JSX namespace, while the
// modern "react-jsx" transform resolves intrinsics through React.JSX. Bridge
// the two so lowercase three.js elements (<points>, <line>, <mesh>, ...) type
// correctly alongside regular DOM elements.
declare module 'react' {
  namespace JSX {
    interface IntrinsicElements extends ThreeElements {}
  }
}
