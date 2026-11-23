import React, { useState } from 'react'
import { useAuth } from '../context/AuthContext';
import { useNavigate } from 'react-router-dom';
import { RiLoader2Fill } from 'react-icons/ri';

const SignUp = ({ setTab, setError }) => {

  const navigate = useNavigate();

  const [username, setUserame] = useState('');
  const [password, setPassword] = useState('');
  const [loader, setLoader] = useState(false);

  const { signup } = useAuth();

  const handleLogin = async (e) => {
    e.preventDefault();
    try {
      setLoader(true)
      if (!username.trim() || !password.trim()) {
        setError('Please fill all the fields');
        return;
      }

      if (username.trim().length < 3) {
        setError('Username must be at least 3 characters');
        return;
      }
      if (password.length < 8) {
        setError('Password must be at least 8 characters');
        return;
      }

      await signup({ username, password })

      setLoader(false)

      navigate('/chat')
    } catch (error) {
      setError(error.message)
    } finally {
      setLoader(false);
    }
  }

  return (
    <div className='flex items-center justify-center px-4 w-full flex-col gap-5'>
      <form onSubmit={handleLogin} className='flex flex-col gap-5 w-full max-w-xs sm:max-w-sm'>
        <div className='w-full'>
          <input
            type="text"
            onChange={(e) => setUserame(e.target.value)}
            value={username}
            placeholder='Enter Username'
            className='w-full py-3 px-6 bg-[#14251a] rounded-full focus:outline-none focus:ring-2 focus:ring-purple-600/50 text-white'
          />
        </div>
        <div className='w-full'>
          <input
            type="password"
            onChange={(e) => setPassword(e.target.value)}
            value={password}
            placeholder='Enter Password'
            className='w-full py-3 px-6 bg-[#14251a] rounded-full focus:outline-none focus:ring-2 focus:ring-purple-600/50 text-white'
          />
          {/* <p className={`w-full text-sm text-white/30 px-3 pt-3 ${(password?.length || 0) >= 8 ? 'hidden' : ''}`}>
            Minimum length : {8 - (password?.length || 0)}
          </p> */}
        </div>
        <div className='w-full'>
          <button
            type='submit'
            className='w-full py-3 bg-purple-600/50 rounded-full text-white hover:bg-purple-600 transition-colors cursor-pointer font-medium focus:outline-none focus:ring-2 focus:ring-purple-600/50'
          >
            {loader ?
              <RiLoader2Fill
                className='animate-spin flex justify-center items-center w-full text-white text-xl' />
              :
              <p>Sign Up</p>}
          </button>
        </div>
      </form>
      <p className='text-white/40 flex gap-1'>
        Already registered ?
        <span
          className='text-purple-600/50 hover:underline hover:text-purple-600 cursor-pointer'
          onClick={() => setTab('login')}
        >
          Login
        </span>
      </p>
    </div>
  )
}

export default SignUp