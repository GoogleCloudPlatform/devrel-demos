import { extend } from "@react-three/fiber";
import { FontLoader } from "three/examples/jsm/Addons.js";
import { TextGeometry } from "three/examples/jsm/Addons.js";
import notoSansMonoRegular from '@/components/noto-sans-mono-regular.json';

extend({ TextGeometry })

export default function Text({ displayText, position, size, rotation=[0,0,0] }: { displayText: number | string, position: [number, number, number], size: number, rotation?: [number, number, number] }) {
  const font = new FontLoader().parse(notoSansMonoRegular);

  return (
    <mesh position={position} rotation={rotation}>
      {/* @ts-expect-error */}
      <textGeometry
        args={[`${displayText}`, { font, size, height: 0 }]}
      />
      <meshPhysicalMaterial attach='material' color={'black'} />
    </mesh>
  )
}




