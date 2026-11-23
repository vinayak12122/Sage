
import React, { useState, useRef, useLayoutEffect } from 'react';
import { TbSendFilled, TbPlayerStopFilled } from "react-icons/tb";
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import { useChat } from '../context/ChatContext';

const MAX_HEIGHT = 200;

const Footer = () => {
  const [message, setMessage] = useState('');
  const [isExpanded, setIsExpanded] = useState(false);
  const textareaRef = useRef(null);

  const navigate = useNavigate();
  const { isAuthenticated } = useAuth();
  const { sendMessage, isStreaming, stopGeneration } = useChat();

  useLayoutEffect(() => {
    const el = textareaRef.current;
    if (!el) return;

    el.style.height = 'auto';

    const newHeight = Math.min(el.scrollHeight, MAX_HEIGHT);
    el.style.height = newHeight + 'px';

    const styles = getComputedStyle(el);
    const singleLineHeight =
      parseFloat(styles.lineHeight) +
      parseFloat(styles.paddingTop) +
      parseFloat(styles.paddingBottom);

    setIsExpanded(el.scrollHeight > singleLineHeight + 1);
  }, [message]);

  const submit = () => {
    const text = message.trim();

    if (!text || isStreaming) return;
    if (!isAuthenticated) return navigate('/auth/login');

    setMessage('');
    sendMessage(text);
  };

  const handleKeyDown = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      submit();
    }
  };

  return (
    <div className='absolute bottom-0.5 w-full flex items-center justify-center my-5'>
      <div className={`bg-[#18271e] md:w-[45%] w-[90%] flex items-end justify-between p-2 gap-2 ${isExpanded ? 'rounded-3xl' : 'rounded-full'
        }`}>
        <textarea
          ref={textareaRef}
          rows={1}
          value={message}
          onChange={e => setMessage(e.target.value)}
          onKeyDown={handleKeyDown}
          placeholder="Let's start chat.."
          className="normal-font outline-none border-none bg-transparent resize-none py-3 px-6 text-lg w-full overflow-y-auto scrollbar-hide"
          style={{ maxHeight: MAX_HEIGHT }}
        />

        {isStreaming ? (
          <button
            type="button"
            onClick={stopGeneration}
            title="Stop generating"
            aria-label="Stop generating"
            className="shrink-0 w-12 h-12 flex items-center justify-center bg-red-500/80 rounded-full hover:bg-red-600 cursor-pointer"
          >
            <TbPlayerStopFilled className="text-xl text-white" />
          </button>
        ) : (
          <button
            type="button"
            onClick={submit}
            disabled={!message.trim()}
            className="shrink-0 w-12 h-12 flex items-center justify-center bg-purple-600/50 rounded-full hover:bg-purple-600 cursor-pointer disabled:opacity-50 disabled:cursor-not-allowed"
          >
            <TbSendFilled className="text-xl" />
          </button>
        )}
      </div>
    </div>
  );
};

export default Footer;
