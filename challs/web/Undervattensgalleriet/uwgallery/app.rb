require 'sinatra'
require "sinatra/multi_route"
require 'sass-embedded'
require 'sequel'
require 'sqlite3'
require 'securerandom'
require 'bcrypt'
require 'time'
require 'sanitize'

set :show_exceptions, false
set :root, File.dirname(__FILE__)
enable :sessions
set :session_secret, '9eeaf760b2a18deef9030f65a4dbf83143d520f283dad1b70447504d8dc01bd6'
set :front_scss, File.read(settings.root + "/assets/frontpage.scss")
DB = Sequel.sqlite('db/app.db')

DB.create_table? :users do
  primary_key :id
  String :username, unique: true, null: false
  String :password, null: false
end

DB.create_table? :galleries do
  primary_key :id
  foreign_key :user_id, :users
  String :title, null: false
  String :path, unique: true, null: false
  DateTime :created_at, default: Sequel::CURRENT_TIMESTAMP
  DateTime :updated_at
end

USERS    = DB[:users]
GALLERIES = DB[:galleries]

helpers do

  def mkgallery(path = rand(36**8).to_s(36))
    unless params[:file] && (tempfile = params[:file][:tempfile]) && (name = params[:file][:filename])
      return path
    end
    d = "#{settings.root}/public/#{path}"
    Dir.mkdir(d) unless File.exist?(d)
    begin
      system("tar x -C #{d} -f #{params[:file][:tempfile].path}")
    rescue
      return nil
    end
    return path
  end

  def bubbles
    front_style = Sass.compile_string(settings.front_scss, style: :compressed).css
    return "<style>#{front_style}</style>" +
    %q(<div id='bubbles'></div>
       <div id='bubbles2'></div>
       <div id='bubbles3'></div>)
  end
end

before do
  if(session[:user])
    begin
      @user = USERS.where(id: session[:user]).first[:username]
    rescue
      session.clear
      @user = nil
    end
  end
end

get '/' do
  erb bubbles +
    %q(<div id='title'>
  <span>
    Undervattensgalleriet
  </span></div>) +
    '<div class="box">Ladda upp dina finaste bilder och få en länk som du kan dela med dina vänner! Fyra bilder per galleri!</div>'
end

get '/new' do
  erb bubbles + %q(
  <div class = "content box">
  <form action="/galleries" method="post" enctype="multipart/form-data">
  <input type="text" name="title">
  <input type="file" name="file" accept=".tar">
  <input type="submit" value="Upload">
</form>
  </div>
  )
end

get '/register', '/login' do
  r = @env["PATH_INFO"] == "/register" ? "register" : "login"
  res = bubbles + %q(
  <div class = "content box">
  <form action="/R" method="post" enctype="multipart/form-data">
  <input type="text" name="user" minlength="1">
  <input type="password" name="password">
  <input type="submit" value="R">
</form>).gsub("R", r)
  if(r == "login")
    res += '<div>(or <a href="/register">register</a>)</div>'
  end
  res += '</div>'
  erb res
end

post "/register" do
  halt 400 unless params[:user] && params[:password]
  begin
    session[:user] = USERS.insert(
      username: params[:user],
      password: BCrypt::Password.create(params[:password])
    )
    redirect "/"
  rescue
    halt 400
  end
end

post "/login" do
  u = USERS.where(username: params[:user]).first or halt 401
  halt 401 unless BCrypt::Password.new(u[:password]) == params[:password]
  session[:user] = u[:id]
  redirect "/"
end

get "/logout" do
  session.clear
  redirect "/"
end

get "/galleries" do
  if(session[:user])
    @galleries = GALLERIES.where(user_id: session[:user]).all
    res = @galleries.map{|g|
      "<div class='row'><a href=/galleries/#{g[:path]}>#{g[:title]}</a></div>"}.join("\n")
    erb bubbles + '<div class = box>' + res + '</div>'
  else
    redirect "/"
  end
end

post "/galleries" do
  redirect "/", erb("") unless session[:user]
  title = Sanitize.clean(params[:title])
  path = mkgallery
  halt 400 unless path
  GALLERIES.insert(user_id: session[:user], title: title, path: path)
  redirect "/galleries/#{path}"
end

put "/galleries/:path" do |path|
  halt 401, erb("") unless session[:user]
  g = GALLERIES.where(
    path: path,
    user_id: session[:user]
  ).first or halt 404
  mkgallery(g[:path])

  title = params[:title] ? Sanitize.clean(params[:title]) : g[:title]

  GALLERIES.where(id: g[:id]).update(
    title: title,
    updated_at: Time.now
  )
  @path = g[:path]
  redirect "/galleries/#{path}"
end

get "/galleries/:path" do |path|
  g = DB[:galleries].where(
    path: path,
  ).first or halt 404, erb(bubbles + '<div class="hero"><img src="/sad-alby.jpg"></div>')
  @title = g[:title]
  @img = Dir.glob(g[:path] + "/*", base: "public")[0..3]
  erb :gallery
end

error do |err|
  `pumactl -P /tmp/puma.pid restart`
end

