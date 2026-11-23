import React, { useState } from 'react'
import { SlNote } from "react-icons/sl";
import { IoDocumentTextOutline } from "react-icons/io5";
import { RxExit } from "react-icons/rx";
import { RxCross2 } from "react-icons/rx";
import { useNavigate } from 'react-router-dom'
import { useAuth } from '../context/AuthContext';
import { useChat } from '../context/ChatContext';


const Sidebar = ({ setOpenSidebar }) => {
    const navigate = useNavigate();

    const { isAuthenticated, logout } = useAuth();
    const {sessions,sessionId} = useChat();

    return (
        <div className="fixed sm:static inset-0 z-50 sm:bg-transparent bg-black/40"
            onClick={() => setOpenSidebar(false)}
        >

            <div className='absolute sm:bottom-10 sm:top-auto top-0 bg-[#14251a] w-[80%] sm:w-80 h-full left-0  sm:h-[80%] px-4 py-4 sm:rounded-3xl flex flex-col gap-4 sm:m-4 '
            onClick={(e)=>e.stopPropagation()}
            >

                <div className='items-center justify-between px-5 sm:hidden flex'
                >
                    <span className='title-font text-2xl cursor-pointer'>Sage</span>
                    <RxCross2
                        className='text-xl text-gray-500 hover:text-white cursor-pointer'
                        onClick={() => setOpenSidebar(false)}
                    />
                </div>
                <div className='px-5 py-2 flex gap-5 hover:bg-[#19462a] rounded-full cursor-pointer items-center'
                    onClick={() => navigate('/chat')}
                >
                    <SlNote
                        className='text-md'
                    />
                    <span>New Chat</span>
                </div>
                <div className='px-5 py-2 flex gap-5 hover:bg-[#19462a] rounded-full cursor-pointer items-center'
                    onClick={() => navigate('/doc')}
                >
                    <IoDocumentTextOutline
                        className='text-lg'
                    />
                    <span>Documentation</span>
                </div>
                <div className=' px-1 flex flex-col gap-2 text-sm flex-1 min-h-0'>
                    <span className='text-white/30 shrink-0'>Chat's</span>
                    <div
                        className='chat-section scrollbar-hide flex flex-col gap-1 py-2 overflow-auto min-h-0'
                    >
                        {sessions.map((s) => (
                            <p
                                key={s.session_id}
                                title={s.preview}
                                onClick={() => { navigate(`/chat/${s.session_id}`); setOpenSidebar(false) }}
                                className={`truncate w-full cursor-pointer px-3 py-1.5 rounded-full hover:bg-[#19462a] ${s.session_id === sessionId ? 'bg-[#19462a]' : ''
                                    }`}
                            >
                                {s.preview}
                            </p>
                        ))}
                    </div>
                </div>
                <div className='w-full flex justify-center md:hidden'>
                    {isAuthenticated ?
                        <div className='flex gap-5 items-center w-full justify-center text-red-500 bg-red-500/20 hover:bg-red-500/30 p-2 rounded-full cursor-pointer'
                            onClick={logout}
                        >
                            <RxExit className='text-lg' />
                            <span className='text-sm'>Sign Out</span>
                        </div>
                        :

                        <div className='flex gap-5 items-center w-full justify-center bg-[#23573554] hover:bg-[#19462a] p-2 rounded-full cursor-pointer '
                            onClick={() => navigate('/auth/login')}
                        >
                            Sign Up
                        </div>
                    }
                </div>
            </div>
        </div>
    )
}

export default Sidebar