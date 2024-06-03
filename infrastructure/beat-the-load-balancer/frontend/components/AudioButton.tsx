'use client'

import React, { memo, useEffect, useState } from 'react'

let audio: HTMLAudioElement;

const toggleAudioVolume = () => {
  if (audio === undefined) {
    console.log('creating audio')
    audio = new Audio('in-game-music.wav');
    audio.volume = 0;
  }
  if (audio.volume === 0) {
    audio.volume = 1;
    audio.play();
    return 1;
  } else {
    audio.volume = 0;
    audio.pause();
    return 0;
  }
}


export default memo(function AudioButton() {
  const [audioVolume, setAudioVolume] = useState(0);

  const handleVolumeClick = () => {
    setAudioVolume(toggleAudioVolume());
  }

  useEffect(() => {
    const handleKeyDown = (event: KeyboardEvent) => {
      switch (event.code) {
        case 'KeyG':
        case 'KeyM':
        case 'KeyV':
          handleVolumeClick();
          return;
      }
    };
    window.addEventListener("keydown", handleKeyDown);

    return () => {
      window.removeEventListener("keydown", handleKeyDown);
    };
  }, []);

  return (
    <div className='flex absolute min-h-screen right-0'>
      <div className='m-auto'>
        {audioVolume === 0 ? (
          <button
            onClick={handleVolumeClick}
            className="group rounded-lg border px-5 py-4 transition-colors hover:bg-gray-100"
          >
            <h2 className={`mb-3 text-5xl`}>
              🔊
            </h2>
            <p className={`mb-3`}>
              Press M for Music
            </p>
          </button>
        ) : (
          <button
            onClick={handleVolumeClick}
            className="group rounded-lg border px-5 py-4 transition-colors hover:bg-gray-100"
          >
            <h2 className={`mb-3 text-5xl`}>
              🔈
            </h2>
            <p className={`mb-3`}>
              Press M to Mute
            </p>
          </button>
        )}
      </div>
    </div>
  );
});
