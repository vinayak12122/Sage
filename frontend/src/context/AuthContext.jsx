import second, { createContext, useContext, useEffect, useState } from 'react'

const AuthContext = createContext(null);

export const AuthProvider = ({ children }) => {
    const backendUrl = import.meta.env.VITE_BACKEND_URL;

    const [user, setUser] = useState(null);
    const [loading, setLoading] = useState(true);

    const checkAuth = async () => {
        try {
            const res = await fetch(`${backendUrl}/auth/me`, {
                credentials: 'include'
            });

            if (res.ok) {
                const data = await res.json();
                setUser(data);
            } else {
                setUser(null);
            }
        } catch (error) {
            console.log('Auth Error : ',error)
            setUser(null);
        }finally{
            setLoading(false);
        }
    }

    const signup = async({username,password}) => {
        const res = await fetch(`${backendUrl}/auth/signup`,{
            method:'POST',
            headers: { "Content-Type": "application/json" },
            body:JSON.stringify({username,password}),
            credentials:'include'
        });

        const data = await res.json();

        if(!res.ok){
            throw new Error(data.detail || 'Signup Failed')
        }
        await checkAuth();

        return data;
    }

    const login = async({username,password}) => {
        const res = await fetch(`${backendUrl}/auth/login`,{
            method:'POST',
            headers:{"Content-Type":"application/json"},
            body:JSON.stringify({username,password}),
            credentials:'include'
        })

        const data = await res.json();

        if(!res.ok){
            throw new Error(data.detail || 'Login Failed');
        }

        await checkAuth();
        return data;
    }

    const logout = async () =>{
        try {
            await fetch(`${backendUrl}/auth/logout`,{
                method:'POST',
                credentials:"include"
            });

            window.location.reload()
        } catch (error) {
            console.error('Logout Error : ',error)
        }finally{
            setUser(null);
        }
    }

    useEffect(()=>{
        checkAuth();
    },[])
    return (
        <AuthContext
        value={{
            user,
            loading,
            login,
            signup,
            logout,
            checkAuth,
            isAuthenticated:!!user
        }}
        >
            {children}
        </AuthContext>
    )
}

export const useAuth = () => useContext(AuthContext);