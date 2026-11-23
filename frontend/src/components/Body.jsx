import React, { useEffect, useRef } from 'react'
import { useChat } from '../context/ChatContext'

const Body = () => {
  const { messages, isStreaming } = useChat();
  const endRef = useRef(null);

  useEffect(() => {
    endRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages])

  

  return (
    <div className="absolute inset-0 flex justify-center overflow-y-auto scrollbar-hide">
      <div className="md:w-[45%] w-[90%] py-6 pb-62 flex flex-col gap-4 min-h-full">

        {messages.length === 0 ? (
          <div className="flex flex-1 items-center justify-center text-center">
            <h2 className="md:text-7xl text-5xl title-font text-white">Welcome to Sage!</h2>
          </div>
        ) : (
          messages.map((m, i) => m.role === 'user' ? (
            <div key={i} className="w-full flex justify-end">
              <p className="w-fit max-w-[75%] bg-purple-600/50 px-4 py-2 rounded-3xl whitespace-pre-wrap wrap-break-words">
                {m.content}
              </p>
            </div>
          ) : (
            <div key={i} className="w-full flex justify-start">

                <p className={`w-fit max-w-full px-4 py-2 whitespace-pre-wrap wrap-break-words ${m.error ? 'text-red-400' : ''}`}>
                  {m.content || (isStreaming && i === messages.length - 1 ? '…' : '')}
                  {m.stopped && (
                    <span className="block text-xs text-gray-500 mt-2">
                      Generation stopped
                    </span>
                  )}
                </p>
            </div>
          ))
        )}

        {messages.length > 0 && <div ref={endRef} className="h-32 shrink-0" />}
      </div>
    </div>
  )
}

export default Body
