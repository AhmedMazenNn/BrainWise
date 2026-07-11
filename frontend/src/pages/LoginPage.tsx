import { useState } from 'react'
import {
  LockKeyholeIcon,
  MailIcon,
  ShieldCheckIcon,
  TruckIcon,
} from 'lucide-react'
import { useForm } from 'react-hook-form'
import { Navigate, useNavigate } from 'react-router-dom'
import { Button, Field, inputClass } from '../components/ui'
import { useAuth } from '../contexts/AuthContext'

interface LoginValues {
  username: string
  password: string
}

export function LoginPage() {
  const { user, login } = useAuth()
  const navigate = useNavigate()
  const {
    register,
    handleSubmit,
    formState: { errors, isSubmitting },
  } = useForm<LoginValues>({
    defaultValues: {
      username: '',
      password: '',
    },
  })
  const [serverError, setServerError] = useState('')

  if (user) return <Navigate to="/" replace />

  const onSubmit = async (values: LoginValues) => {
    setServerError('')
    try {
      await login(values.username, values.password)
      navigate('/')
    } catch (error: unknown) {
      const msg =
        axios.isAxiosError(error) && error.response?.data?.detail
          ? String(error.response.data.detail)
          : error instanceof Error
            ? error.message
            : 'Unable to sign in.'
      setServerError(msg)
    }
  }

  return (
    <main className="grid min-h-screen w-full bg-[#f5f7f7] lg:grid-cols-[1.05fr_0.95fr]">
      <section className="hidden bg-[#173f3c] p-12 text-white lg:flex lg:flex-col lg:justify-between">
        <div className="flex items-center gap-2.5">
          <div className="grid h-9 w-9 place-items-center rounded-lg bg-white text-base font-bold text-[#175e58]">
            N
          </div>
          <span className="font-bold tracking-tight">Northstar Logistics</span>
        </div>
        <div className="max-w-md">
          <div className="mb-7 grid h-14 w-14 place-items-center rounded-2xl border border-white/15 bg-white/10">
            <TruckIcon size={27} />
          </div>
          <h1 className="text-4xl font-bold leading-tight tracking-tight">
            Every delivery, clearly in view.
          </h1>
          <p className="mt-5 text-lg leading-8 text-emerald-50/75">
            A focused operations workspace for teams that keep commerce moving.
          </p>
        </div>
        <div className="flex items-center gap-3 text-sm text-emerald-50/70">
          <ShieldCheckIcon size={18} />
          Secure internal operations platform
        </div>
      </section>
      <section className="flex items-center justify-center p-5 sm:p-10">
        <div className="w-full max-w-[390px]">
          <div className="mb-10 lg:hidden">
            <div className="flex items-center gap-2.5">
              <div className="grid h-9 w-9 place-items-center rounded-lg bg-[#175e58] font-bold text-white">
                N
              </div>
              <span className="font-bold text-slate-900">
                Northstar Logistics
              </span>
            </div>
          </div>
          <p className="text-sm font-semibold text-[#175e58]">
            INTERNAL ACCESS
          </p>
          <h1 className="mt-2 text-3xl font-bold tracking-tight text-slate-900">
            Welcome back
          </h1>
          <p className="mt-2 text-sm leading-6 text-slate-500">
            Sign in to manage today's delivery operations.
          </p>
          <form
            onSubmit={handleSubmit(onSubmit)}
            className="mt-8 space-y-5"
            noValidate
          >
            {serverError && (
              <div
                role="alert"
                className="rounded-lg border border-red-100 bg-red-50 px-3 py-2.5 text-sm text-red-700"
              >
                {serverError}
              </div>
            )}
            <Field label="Username" error={errors.username?.message}>
              <div className="relative">
                <MailIcon
                  size={16}
                  className="absolute left-3 top-3 text-slate-400"
                />
                <input
                  className={`${inputClass} pl-9`}
                  autoComplete="username"
                  {...register('username', {
                    required: 'Enter your username',
                  })}
                />
              </div>
            </Field>
            <Field label="Password" error={errors.password?.message}>
              <div className="relative">
                <LockKeyholeIcon
                  size={16}
                  className="absolute left-3 top-3 text-slate-400"
                />
                <input
                  className={`${inputClass} pl-9`}
                  type="password"
                  autoComplete="current-password"
                  {...register('password', {
                    required: 'Enter your password',
                  })}
                />
              </div>
            </Field>
            <Button
              loading={isSubmitting}
              type="submit"
              className="mt-2 w-full"
            >
              Sign in to workspace
            </Button>
          </form>
          <div className="mt-7 rounded-lg border border-slate-200 bg-white p-3.5 text-xs leading-5 text-slate-500">
            <span className="font-bold text-slate-700">Demo accounts</span>
            <br />
            Manager: admin / Driver: driver
            <br />
            Password: testpass123
          </div>
        </div>
      </section>
    </main>
  )
}

import axios from 'axios'
