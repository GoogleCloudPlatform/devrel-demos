"use client";

import Image from "next/image";
import styles from "./page.module.css";

import Chat from "./chat";
import { useRef, useState } from "react";

const items = [
  {
    title: "Baby Bluebird",
    price: "19.99",
    image: "bird",
  },
  {
    title: "Lil' Lamb",
    price: "7.99",
    image: "lamb",
  },
  {
    title: "Allie",
    price: "12.99",
    image: "allie",
  },
  {
    title: "Wooden Trio",
    price: "22.99",
    image: "wooden",
  },
  {
    title: "Slouch",
    price: "24.99",
    image: "slouch",
  },
  {
    title: "Splat",
    price: "24.99",
    image: "splat",
  },
];

export default function Home() {
  const [chatOpen, setChatOpen] = useState(false);
  const [cartNumber, setCartNumber] = useState(false);
  const textAreaRef = useRef<HTMLTextAreaElement>(null);

  function handleChatClick() {
    if (chatOpen) {
      setChatOpen(false);
    } else {
      setChatOpen(true);
      textAreaRef.current?.focus();
    }
  }

  function handleCallback() {
    setChatOpen(false);
    setCartNumber(true);
  }

  return (
    <main>
      <div className={styles.shipping}>Free shipping on orders over $100</div>
      <div className={styles.menu}>
        <div className={styles.menuInner}>
          <Image alt="logo" src="/logo.svg" width="120" height="50" />
          <div className={styles.cartNumberWrapper}>
            <Image alt="cart" src="/cart.svg" width="30" height="30" />
            {cartNumber && <div className={styles.cartNumber}>1</div>}
          </div>
        </div>
      </div>
      <div className={styles.body}>
        <div>
          <Image alt="toyshop" src="/toyshop.jpg" width="491" height="809" />
        </div>
        <div className={styles.right}>
          <div className={styles.header}>
            <h1>For Kids</h1>
            <div className={styles.chat} onClick={handleChatClick}>
              <Image alt="open chat" src="/chat.svg" width="30" height="30" />
            </div>
            {
              <Chat
                isOpen={chatOpen}
                callback={handleCallback}
                textAreaRef={textAreaRef}
              />
            }
          </div>
          <div className={styles.grid}>
            {items.map((item) => (
              <div key={item.title} className={styles.item}>
                <Image
                  alt={item.title}
                  className={styles.title}
                  src={`/${item.image}.png`}
                  width="213"
                  height="213"
                />
                <div>{item.title}</div>
                <div>${item.price}</div>
              </div>
            ))}
          </div>
        </div>
      </div>
    </main>
  );
}
