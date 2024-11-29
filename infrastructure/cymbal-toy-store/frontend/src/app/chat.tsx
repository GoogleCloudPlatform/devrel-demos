// Copyright 2024 Google LLC.
//
// Licensed under the Apache License, Version 2.0 (the "License");
// you may not use this file except in compliance with the License.
// You may obtain a copy of the License at
//
//     http://www.apache.org/licenses/LICENSE-2.0
//
// Unless required by applicable law or agreed to in writing, software
// distributed under the License is distributed on an "AS IS" BASIS,
// WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
// See the License for the specific language governing permissions and
// limitations under the License.

import React, { FormEventHandler, useEffect, useRef, useState } from "react";
import { api } from "@/app/api";
import Image from "next/image";
import Link from 'next/link';
import ReactMarkdown from 'react-markdown';

import styles from "./chat.module.css";

export default function Chat({
  callback,
  isOpen,
  textAreaRef,
}: {
  callback: () => void;
  isOpen: boolean;
  textAreaRef: React.RefObject<HTMLTextAreaElement>;
}) {
  const [data, setData] = useState([
    {
      text: "Welcome to Cymbal support! How can I help you today?",
      role: "assistant",
      image:  "",
    },
  ]);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const formRef = useRef<HTMLFormElement>(null);

  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [showExtra, setShowExtra] = useState(true);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({
      behavior: "smooth",
      block: "nearest",
      inline: "start",
    });
  }, [data]);

  function handleInput(evt: React.ChangeEvent<HTMLTextAreaElement>) {
    setInput(evt.target.value);

    if (!textAreaRef?.current) return;
    textAreaRef.current.style.height = "";
    textAreaRef.current.style.height = textAreaRef.current.scrollHeight + "px";
  }

  async function handleSubmit(evt: React.FormEvent<HTMLFormElement>) {
    evt.preventDefault();

    setInput("");
    if (textAreaRef.current) {
      textAreaRef.current.style.height = "";
    }

    const newData = [...data, { text: input, role: "user", image:"" }];
    setData(newData);

    setLoading(true);
    console.log(newData.slice(1))
    const response = await api(newData.slice(1));
    const body = await response.json();
    setLoading(false);

    setData([...newData, { text: body.content.text, role: "assistant", image: body.image_url.image_url.url }]);
    setShowExtra(true);
  }

  function handleAddToCart() {
    callback();
  }

  function handleKeyDown(evt: React.KeyboardEvent<HTMLTextAreaElement>) {
    if (evt.key == "Enter" && !evt.shiftKey) {
      handleSubmit(evt as unknown as React.FormEvent<HTMLFormElement>);
    }
  }
  //Image uploader
  const [selectedImage, setSelectedImage] = useState<string | null>(null);
  const [base64Image, setBase64Image] = useState<string | null>(null);

function handleImageChange(event: React.ChangeEvent<HTMLInputElement>) {
    
    if (event.target.files && event.target.files[0]) {
      setSelectedImage(URL.createObjectURL(event.target.files[0]));
      const file = event.target.files[0]; // Get the file
      if (file) {
        const reader = new FileReader(); // Create FileReader to convert to Base64
        reader.onloadend = () => {
          
          setBase64Image(reader.result as string);
          const base64data = reader.result; // Get Base64 data
          var image_base64 = "data:image/jpeg;base64," + base64data
          const newData = [...data, { text: "Please describe this image", image_url: { url: base64data}, role: "user" , image: ""}];
          setData(newData);
          setLoading(true);
          console.log(newData.slice(1))
          api(newData.slice(1))
            .then(response => response.json())
            .then(body => setData([...newData, { text: body.content.text, role: "assistant", image: body.image_url.image_url.url }]))
          setLoading(false);
          setShowExtra(true);
        };
        reader.readAsDataURL(file); // Convert to Base64
      }
    }
  }

  return (
    <div
      className={[styles.wrapper, isOpen ? styles.wrapperOpen : ""].join(" ")}
    >
      <div className={styles.messages}>
        {data.map((item, idx) => (
          <div
            className={
              item.role === "assistant" ? styles.assistant : styles.user
            }
            key={idx}
          >
            <ReactMarkdown>{item.text}</ReactMarkdown>
            <br></br>
            {item.image && (
              <img src={item.image} width="100" height="100" />
            )}           
          </div>
        ))}
        {loading && (
          <div className={[styles.loaderWrapper, styles.assistant].join(" ")}>
            <div className={styles.loader}></div>
          </div>
        )}
        {showExtra && (
          <div className={styles.extra}>
            <button
              className={styles.addToCartButton}
              onClick={handleAddToCart}
            >
              <Image alt="send" src="/cart_add.svg" height="30" width="30" />
              Add to cart
            </button>
            <Link className={styles.addToCartButton} href="https://toys-uxu5wi2jpa-uc.a.run.app" target="_blank">
            <Image alt="send" src="/camera.svg" height="30" width="30" />
            Toys like this!
            </Link>
            {/* Image uploader */}
            <label htmlFor="image-upload" className={styles.imageFileupload}>
              <Image alt="send" src="/add_picture.svg" height="30" width="30" />
              <span>Upload Image</span> {/* Custom caption */}
              <input 
                type="file" 
                id="image-upload"
                accept="image/*" 
                onChange={handleImageChange}
              />
            </label>
          </div>
        )}
        <div ref={messagesEndRef}></div>
      </div>
      <div className={styles.footer}>
        <form ref={formRef} className={styles.form} onSubmit={handleSubmit}>
          <textarea
            className={styles.input}
            value={input}
            ref={textAreaRef}
            onChange={handleInput}
            onKeyDown={handleKeyDown}
            rows={1}
            placeholder="Write a message"
          />
          <button className={styles.button} type="submit">
            <Image alt="send" src="/send.svg" height="20" width="20" />
          </button>
        </form>
      </div>
    </div>
  );
}
