import React, { useEffect, useState } from 'react';
import Login from '../components/Login';
import SignUp from '../components/SignUp';
import { FaC, FaChevronLeft } from "react-icons/fa6";
import { useNavigate } from 'react-router-dom';

const AuthPage = () => {
    const [tab, setTab] = useState('login');
    const [error, setError] = useState('');

    const navigate = useNavigate();

    useEffect(() => {
        if (!error) {
            return
        }

        const timer = setTimeout(() => {
            setError('')
        }, 3000)

        return () => clearTimeout(timer)
    }, [error])

    const handleTabChange = (newTab) => {
        setError('');
        setTab(newTab);
    };

    return (
        <div className="relative min-h-screen flex flex-col items-center justify-center">
            <span className='fixed top-5 left-5 sm:left-10'>
                <FaChevronLeft
                    className='text-4xl p-2.5 rounded-full hover:bg-[#14251a] cursor-pointer'
                    onClick={() => navigate(-1)}
                />
            </span>
            <span className="absolute top-[20%] h-10 flex items-center title-font text-6xl select-none">
                Sage
            </span>
            {tab === 'login' ? (
                <Login setTab={handleTabChange} setError={setError} />
            ) : (
                <SignUp setTab={handleTabChange} setError={setError} />
            )}

            {error && (
                <div className="absolute bottom-[20%] bg-red-500/20 text-red-400 px-4 py-2 rounded-full">
                    {error}
                </div>
            )}
        </div>
    );
};

export default AuthPage;